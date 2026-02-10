"""Team service layer with fuzzy matching and caching."""

import asyncio

import structlog
from thefuzz import fuzz, process

from cbb_mcp.models.games import Game
from cbb_mcp.models.teams import Player, Team
from cbb_mcp.services.resolver import resolve
from cbb_mcp.sources.base import DataCapability
from cbb_mcp.utils import cache
from cbb_mcp.utils.constants import CACHE_TTL
from cbb_mcp.utils.errors import TeamNotFoundError

logger = structlog.get_logger()

# In-memory team name -> ID cache for fuzzy matching
_team_cache: dict[str, Team] = {}
_cache_lock = asyncio.Lock()


async def _ensure_team_cache() -> None:
    """Populate team cache if empty (thread-safe)."""
    if _team_cache:
        return
    async with _cache_lock:
        if _team_cache:  # double-check after acquiring lock
            return
        try:
            teams = await resolve(
                DataCapability.TEAM_SEARCH, "search_teams", query=""
            )
            for t in teams:
                _team_cache[t.name.lower()] = t
                if t.abbreviation:
                    _team_cache[t.abbreviation.lower()] = t
                if t.mascot:
                    _team_cache[t.mascot.lower()] = t
        except Exception:
            logger.debug("team_cache_init_failed", msg="Will use direct lookups")


async def fuzzy_find_team(query: str) -> Team:
    """Find a team by fuzzy matching on name, abbreviation, or mascot."""
    await _ensure_team_cache()

    query_lower = query.lower().strip()

    # Exact match
    if query_lower in _team_cache:
        return _team_cache[query_lower]

    # Fuzzy match
    if _team_cache:
        names = list(_team_cache.keys())
        result = process.extractOne(query_lower, names, scorer=fuzz.token_sort_ratio)
        if result and result[1] >= 60:
            return _team_cache[result[0]]

    # Fall back to search API
    teams = await resolve(
        DataCapability.TEAM_SEARCH, "search_teams", query=query
    )
    if teams:
        return teams[0]

    raise TeamNotFoundError(query)


async def get_team(query: str) -> Team:
    """Look up a team by name (fuzzy matched)."""
    cached = cache.get("team_info", query.lower())
    if cached:
        return Team(**cached) if isinstance(cached, dict) else cached

    team = await fuzzy_find_team(query)

    # If we only have basic info, try to get full details
    if team.id and not team.record.wins:
        try:
            full_team = await resolve(
                DataCapability.TEAM_INFO, "get_team", team_id=team.id
            )
            if full_team:
                team = full_team
        except Exception:
            pass

    cache.put(
        "team_info", query.lower(), data=team.model_dump(), ttl=CACHE_TTL["team_info"]
    )
    return team


async def search_teams(query: str, conference: str = "") -> list[Team]:
    """Search teams by name/conference."""
    return await resolve(
        DataCapability.TEAM_SEARCH,
        "search_teams",
        query=query,
        conference=conference,
    )


async def get_roster(team_query: str) -> tuple[Team, list[Player]]:
    """Get roster for a team (fuzzy matched)."""
    team = await fuzzy_find_team(team_query)
    cached = cache.get("roster", team.id)
    if cached:
        players = [Player(**p) if isinstance(p, dict) else p for p in cached]
        return team, players

    players = await resolve(
        DataCapability.ROSTER, "get_roster", team_id=team.id
    )
    cache.put(
        "roster", team.id, data=[p.model_dump() for p in players], ttl=CACHE_TTL["roster"]
    )
    return team, players


async def get_schedule(team_query: str, season: int = 0) -> tuple[Team, list[Game]]:
    """Get schedule for a team (fuzzy matched)."""
    team = await fuzzy_find_team(team_query)
    cache_key = f"{team.id}:{season}"
    cached = cache.get("team_schedule", cache_key)
    if cached:
        games = [Game(**g) if isinstance(g, dict) else g for g in cached]
        return team, games

    games = await resolve(
        DataCapability.SCHEDULE,
        "get_schedule",
        team_id=team.id,
        season=season,
    )
    cache.put(
        "team_schedule",
        cache_key,
        data=[g.model_dump() for g in games],
        ttl=CACHE_TTL["team_schedule"],
    )
    return team, games

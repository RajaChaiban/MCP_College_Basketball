"""Statistics service layer."""

from cbb_mcp.models.stats import PlayerStats, StatLeader, TeamComparison, TeamStats
from cbb_mcp.services.resolver import resolve
from cbb_mcp.services.teams import fuzzy_find_team
from cbb_mcp.sources.base import DataCapability
from cbb_mcp.utils import cache
from cbb_mcp.utils.constants import CACHE_TTL


async def get_team_stats(team_query: str, season: int = 0) -> TeamStats:
    team = await fuzzy_find_team(team_query)
    cache_key = f"{team.id}:{season}"
    cached = cache.get("team_stats", cache_key)
    if cached:
        return TeamStats(**cached) if isinstance(cached, dict) else cached

    stats = await resolve(
        DataCapability.TEAM_STATS,
        "get_team_stats",
        team_id=team.id,
        season=season,
    )
    if not stats.team_name:
        stats.team_name = team.name
    stats.team_id = team.id

    cache.put(
        "team_stats", cache_key, data=stats.model_dump(), ttl=CACHE_TTL["team_stats"]
    )
    return stats


async def get_player_stats(
    team_query: str = "", player_id: str = ""
) -> list[PlayerStats]:
    team = await fuzzy_find_team(team_query) if team_query else None
    team_id = team.id if team else ""

    cache_key = f"{team_id}:{player_id}"
    cached = cache.get("player_stats", cache_key)
    if cached:
        return [PlayerStats(**p) if isinstance(p, dict) else p for p in cached]

    players = await resolve(
        DataCapability.PLAYER_STATS,
        "get_player_stats",
        player_id=player_id,
        team_id=team_id,
    )
    cache.put(
        "player_stats",
        cache_key,
        data=[p.model_dump() for p in players],
        ttl=CACHE_TTL["player_stats"],
    )
    return players


async def get_stat_leaders(
    category: str = "scoring", season: int = 0
) -> list[StatLeader]:
    cache_key = f"{category}:{season}"
    cached = cache.get("stat_leaders", cache_key)
    if cached:
        return [StatLeader(**l) if isinstance(l, dict) else l for l in cached]

    leaders = await resolve(
        DataCapability.STAT_LEADERS,
        "get_stat_leaders",
        category=category,
        season=season,
    )
    cache.put(
        "stat_leaders",
        cache_key,
        data=[l.model_dump() for l in leaders],
        ttl=CACHE_TTL["stat_leaders"],
    )
    return leaders


async def compare_teams(team1_query: str, team2_query: str) -> TeamComparison:
    stats1 = await get_team_stats(team1_query)
    stats2 = await get_team_stats(team2_query)

    advantages: dict[str, str] = {}
    comparisons = [
        ("ppg", "Points Per Game", True),
        ("opp_ppg", "Opp Points Per Game", False),  # lower is better
        ("fg_pct", "FG%", True),
        ("three_pct", "3PT%", True),
        ("ft_pct", "FT%", True),
        ("rpg", "Rebounds Per Game", True),
        ("apg", "Assists Per Game", True),
        ("spg", "Steals Per Game", True),
        ("bpg", "Blocks Per Game", True),
        ("topg", "Turnovers Per Game", False),  # lower is better
    ]

    for attr, label, higher_better in comparisons:
        v1 = getattr(stats1, attr, 0)
        v2 = getattr(stats2, attr, 0)
        if v1 == v2:
            advantages[label] = "Even"
        elif (v1 > v2) == higher_better:
            advantages[label] = stats1.team_name
        else:
            advantages[label] = stats2.team_name

    return TeamComparison(team1=stats1, team2=stats2, advantages=advantages)

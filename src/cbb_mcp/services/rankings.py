"""Rankings and standings service layer."""

from cbb_mcp.models.rankings import ConferenceStandings, Poll
from cbb_mcp.services.resolver import resolve
from cbb_mcp.sources.base import DataCapability
from cbb_mcp.utils import cache
from cbb_mcp.utils.constants import CACHE_TTL


async def get_rankings(
    poll_type: str = "ap", season: int = 0, week: int = 0
) -> Poll:
    cache_key_args = [poll_type, str(season), str(week)]
    cached = cache.get("rankings", *cache_key_args)
    if cached:
        return Poll(**cached) if isinstance(cached, dict) else cached

    poll = await resolve(
        DataCapability.RANKINGS,
        "get_rankings",
        poll_type=poll_type,
        season=season,
        week=week,
    )
    cache.put(
        "rankings", *cache_key_args, data=poll.model_dump(), ttl=CACHE_TTL["rankings"]
    )
    return poll


async def get_standings(conference: str = "") -> list[ConferenceStandings]:
    cached = cache.get("standings", conference)
    if cached:
        return [
            ConferenceStandings(**s) if isinstance(s, dict) else s for s in cached
        ]

    standings = await resolve(
        DataCapability.STANDINGS,
        "get_standings",
        conference=conference,
    )
    cache.put(
        "standings",
        conference,
        data=[s.model_dump() for s in standings],
        ttl=CACHE_TTL["standings"],
    )
    return standings

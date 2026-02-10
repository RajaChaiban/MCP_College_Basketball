"""Source priority resolver with automatic fallback."""

from typing import Any

import structlog

from cbb_mcp.config import settings
from cbb_mcp.sources.base import DataCapability, DataSource
from cbb_mcp.sources.cbbpy_source import CbbpySource
from cbb_mcp.sources.espn import ESPNSource
from cbb_mcp.sources.ncaa import NCAASource
from cbb_mcp.sources.sportsdataverse import SportsdataverseSource
from cbb_mcp.utils.errors import AllSourcesFailedError, SourceError
from cbb_mcp.utils.rate_limiter import get_limiter

logger = structlog.get_logger()

# Whitelist of allowed method names that can be called on sources.
_ALLOWED_METHODS: frozenset[str] = frozenset({
    "get_live_scores",
    "get_team",
    "search_teams",
    "get_roster",
    "get_schedule",
    "get_game_detail",
    "get_box_score",
    "get_play_by_play",
    "get_rankings",
    "get_standings",
    "get_team_stats",
    "get_player_stats",
    "get_stat_leaders",
})

# Instantiate all sources
_sources: list[DataSource] = sorted(
    [ESPNSource(), NCAASource(), SportsdataverseSource(), CbbpySource()],
    key=lambda s: s.priority,
)

# Rate limit map
_rate_limits: dict[str, float] = {
    "espn": settings.espn_rate_limit,
    "ncaa": settings.ncaa_rate_limit,
    "sportsdataverse": 5,
    "cbbpy": 3,
}


def get_sources_for(capability: DataCapability) -> list[DataSource]:
    """Return sources that support a given capability, ordered by priority."""
    return [s for s in _sources if capability in s.capabilities()]


async def resolve(
    capability: DataCapability,
    method_name: str,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Try each source in priority order until one succeeds.

    Args:
        capability: The data capability needed.
        method_name: Name of the method to call on the source (must be whitelisted).
        *args, **kwargs: Arguments passed to the source method.

    Returns:
        The result from the first successful source.

    Raises:
        AllSourcesFailedError: If no source can fulfill the request.
        ValueError: If method_name is not in the allowed whitelist.
    """
    if method_name not in _ALLOWED_METHODS:
        raise ValueError(f"Method not allowed: {method_name}")

    sources = get_sources_for(capability)
    if not sources:
        raise AllSourcesFailedError(capability.name, [])

    errors: list[SourceError] = []

    for source in sources:
        method = getattr(source, method_name, None)
        if not method:
            continue

        try:
            limiter = get_limiter(source.name, _rate_limits.get(source.name, 5))
            await limiter.acquire()

            result = await method(*args, **kwargs)
            logger.debug(
                "source_resolved",
                source=source.name,
                capability=capability.name,
                method=method_name,
            )
            return result

        except SourceError as e:
            logger.warning(
                "source_failed",
                source=source.name,
                capability=capability.name,
                error=str(e),
            )
            errors.append(e)
        except Exception as e:
            err = SourceError(source.name, str(e))
            logger.warning(
                "source_failed_unexpected",
                source=source.name,
                capability=capability.name,
                error_type=type(e).__name__,
            )
            errors.append(err)

    raise AllSourcesFailedError(capability.name, errors)

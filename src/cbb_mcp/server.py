"""MCP server: tool registrations, resources, prompts, entry point."""

import asyncio
import hmac
import logging
import re
import sys
from datetime import date, datetime

import structlog

from mcp.server.fastmcp import FastMCP

from cbb_mcp.config import settings
from cbb_mcp.services import games, rankings, stats, teams
from cbb_mcp.utils import formatting
from cbb_mcp.utils.constants import ESPN_CONFERENCES, CURRENT_SEASON
from cbb_mcp.utils.errors import CBBError

_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_level_name = settings.log_level.upper() if settings.log_level.upper() in _LOG_LEVELS else "INFO"
_log_level = getattr(logging, _level_name)

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(_log_level),
)

logger = structlog.get_logger()

# Global semaphore: cap concurrent in-flight tool calls to prevent resource exhaustion
_MAX_CONCURRENT_CALLS = 50
_concurrency = asyncio.Semaphore(_MAX_CONCURRENT_CALLS)

mcp = FastMCP(
    "College Basketball",
    instructions="NCAA Men's D1 College Basketball data — live scores, teams, rankings, stats, and more",
)

# ═══════════════════════════════════════════════════════════════
# Input validation
# ═══════════════════════════════════════════════════════════════

MAX_INPUT_LEN = 200
_GAME_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,30}$")


def _sanitize_text(text: str, field: str = "input") -> str:
    """Validate and sanitize text input."""
    if len(text) > MAX_INPUT_LEN:
        raise CBBError(f"{field} too long (max {MAX_INPUT_LEN} characters)")
    return text.strip()


def _validate_game_id(game_id: str) -> str:
    """Validate a game ID is alphanumeric."""
    game_id = game_id.strip()
    if not _GAME_ID_RE.match(game_id):
        raise CBBError("Invalid game ID format")
    return game_id


def _today() -> str:
    return date.today().isoformat()


def _validate_date(d: str) -> str:
    """Validate and normalize a date string to YYYY-MM-DD."""
    if not d:
        return _today()
    d = d.strip()
    if len(d) > 20:
        raise CBBError("Invalid date format")
    try:
        parsed = date.fromisoformat(d)
        return parsed.isoformat()
    except ValueError:
        for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%Y%m%d"):
            try:
                parsed = datetime.strptime(d, fmt).date()
                return parsed.isoformat()
            except ValueError:
                continue
    raise CBBError(f"Unrecognized date format: {d}. Use YYYY-MM-DD.")


def _validate_season(season: int) -> int:
    """Validate season year is reasonable."""
    if season == 0:
        return 0
    if not (2000 <= season <= 2100):
        raise CBBError("Season must be between 2000 and 2100")
    return season


# ═══════════════════════════════════════════════════════════════
# Team Tools
# ═══════════════════════════════════════════════════════════════

@mcp.tool()
async def get_team(team_name: str) -> str:
    """Look up a college basketball team by name (fuzzy matched).
    Returns team info including record, conference, and venue.

    Args:
        team_name: Team name, abbreviation, or mascot (e.g., "Duke", "UNC", "Wildcats")
    """
    async with _concurrency:
        try:
            team_name = _sanitize_text(team_name, "team_name")
            team = await teams.get_team(team_name)
            return formatting.format_team(team)
        except CBBError as e:
            return str(e)
        except Exception:
            logger.exception("unexpected_error", tool="get_team")
            return "An unexpected error occurred. Please try again."


@mcp.tool()
async def search_teams(query: str, conference: str = "") -> str:
    """Search for college basketball teams by name or conference.

    Args:
        query: Search query (team name, city, abbreviation)
        conference: Optional conference filter (e.g., "ACC", "Big Ten", "SEC")
    """
    async with _concurrency:
        try:
            query = _sanitize_text(query, "query")
            if conference:
                conference = _sanitize_text(conference, "conference")
            result = await teams.search_teams(query, conference)
            if not result:
                return f"No teams found matching '{query}'."
            lines = [f"Found {len(result)} team(s):\n"]
            for t in result[:20]:
                rank = f"#{t.rank} " if t.rank else ""
                lines.append(f"  {rank}{t.name} ({t.abbreviation}) — {t.conference}")
            return "\n".join(lines)
        except CBBError as e:
            return str(e)
        except Exception:
            logger.exception("unexpected_error", tool="search_teams")
            return "An unexpected error occurred. Please try again."


@mcp.tool()
async def get_team_roster(team_name: str) -> str:
    """Get the full roster for a college basketball team.

    Args:
        team_name: Team name (fuzzy matched)
    """
    async with _concurrency:
        try:
            team_name = _sanitize_text(team_name, "team_name")
            team, players = await teams.get_roster(team_name)
            return formatting.format_roster(team, players)
        except CBBError as e:
            return str(e)
        except Exception:
            logger.exception("unexpected_error", tool="get_team_roster")
            return "An unexpected error occurred. Please try again."


@mcp.tool()
async def get_team_schedule(team_name: str, season: int = 0) -> str:
    """Get the complete schedule for a college basketball team, including results
    for completed games and upcoming matchups.

    Args:
        team_name: Team name (fuzzy matched)
        season: Season year (e.g., 2025 for 2024-25 season). Defaults to current season.
    """
    async with _concurrency:
        try:
            team_name = _sanitize_text(team_name, "team_name")
            season = _validate_season(season)
            team, schedule = await teams.get_schedule(team_name, season)
            return formatting.format_schedule(team, schedule)
        except CBBError as e:
            return str(e)
        except Exception:
            logger.exception("unexpected_error", tool="get_team_schedule")
            return "An unexpected error occurred. Please try again."


# ═══════════════════════════════════════════════════════════════
# Game / Score Tools
# ═══════════════════════════════════════════════════════════════

@mcp.tool()
async def get_live_scores(
    date: str = "", conference: str = "", top25_only: bool = False
) -> str:
    """Get live and final college basketball scores for a given date.

    Args:
        date: Date in YYYY-MM-DD format. Defaults to today.
        conference: Optional conference filter (e.g., "ACC", "Big Ten")
        top25_only: If true, only show games involving ranked teams
    """
    async with _concurrency:
        try:
            d = _validate_date(date)
            if conference:
                conference = _sanitize_text(conference, "conference")
            result = await games.get_live_scores(d, conference, top25_only)
            header = f"**College Basketball Scores — {d}**"
            if conference:
                header += f" ({conference})"
            if top25_only:
                header += " (Top 25 only)"
            return header + "\n\n" + formatting.format_scores(result)
        except CBBError as e:
            return str(e)
        except Exception:
            logger.exception("unexpected_error", tool="get_live_scores")
            return "An unexpected error occurred. Please try again."


@mcp.tool()
async def get_game_detail(game_id: str) -> str:
    """Get comprehensive details for a specific game including scoring summary.

    Args:
        game_id: ESPN game ID
    """
    async with _concurrency:
        try:
            game_id = _validate_game_id(game_id)
            game = await games.get_game_detail(game_id)
            return formatting.format_game_detail(game)
        except CBBError as e:
            return str(e)
        except Exception:
            logger.exception("unexpected_error", tool="get_game_detail")
            return "An unexpected error occurred. Please try again."


@mcp.tool()
async def get_box_score(game_id: str) -> str:
    """Get detailed per-player and team box score for a game.

    Args:
        game_id: ESPN game ID
    """
    async with _concurrency:
        try:
            game_id = _validate_game_id(game_id)
            box = await games.get_box_score(game_id)
            return formatting.format_box_score(box)
        except CBBError as e:
            return str(e)
        except Exception:
            logger.exception("unexpected_error", tool="get_box_score")
            return "An unexpected error occurred. Please try again."


@mcp.tool()
async def get_play_by_play(game_id: str, last_n: int = 20) -> str:
    """Get play-by-play data for a game.

    Args:
        game_id: ESPN game ID
        last_n: Number of most recent plays to show (0 for all). Defaults to 20.
    """
    async with _concurrency:
        try:
            game_id = _validate_game_id(game_id)
            last_n = max(0, min(last_n, 500))
            pbp = await games.get_play_by_play(game_id)
            return formatting.format_play_by_play(pbp, last_n)
        except CBBError as e:
            return str(e)
        except Exception:
            logger.exception("unexpected_error", tool="get_play_by_play")
            return "An unexpected error occurred. Please try again."


# ═══════════════════════════════════════════════════════════════
# Rankings / Standings
# ═══════════════════════════════════════════════════════════════

@mcp.tool()
async def get_rankings(
    poll: str = "ap", season: int = 0, week: int = 0
) -> str:
    """Get college basketball poll rankings (AP Top 25, Coaches Poll).

    Args:
        poll: Poll type — "ap" (default) or "coaches"
        season: Season year. Defaults to current season.
        week: Specific week number. Defaults to latest.
    """
    async with _concurrency:
        try:
            poll = _sanitize_text(poll, "poll")
            season = _validate_season(season)
            result = await rankings.get_rankings(poll, season, week)
            return formatting.format_rankings(result)
        except CBBError as e:
            return str(e)
        except Exception:
            logger.exception("unexpected_error", tool="get_rankings")
            return "An unexpected error occurred. Please try again."


@mcp.tool()
async def get_standings(conference: str = "") -> str:
    """Get conference standings with records and streaks.

    Args:
        conference: Conference name (e.g., "ACC", "Big Ten"). Leave empty for all conferences.
    """
    async with _concurrency:
        try:
            if conference:
                conference = _sanitize_text(conference, "conference")
            result = await rankings.get_standings(conference)
            return formatting.format_standings(result)
        except CBBError as e:
            return str(e)
        except Exception:
            logger.exception("unexpected_error", tool="get_standings")
            return "An unexpected error occurred. Please try again."


# ═══════════════════════════════════════════════════════════════
# Statistics
# ═══════════════════════════════════════════════════════════════

@mcp.tool()
async def get_team_stats(team_name: str, season: int = 0) -> str:
    """Get season statistics for a team (PPG, FG%, rebounds, assists, etc.).

    Args:
        team_name: Team name (fuzzy matched)
        season: Season year. Defaults to current season.
    """
    async with _concurrency:
        try:
            team_name = _sanitize_text(team_name, "team_name")
            season = _validate_season(season)
            result = await stats.get_team_stats(team_name, season)
            return formatting.format_team_stats(result)
        except CBBError as e:
            return str(e)
        except Exception:
            logger.exception("unexpected_error", tool="get_team_stats")
            return "An unexpected error occurred. Please try again."


@mcp.tool()
async def get_player_stats(team_name: str) -> str:
    """Get individual player season statistics for all players on a team.

    Args:
        team_name: Team name (fuzzy matched)
    """
    async with _concurrency:
        try:
            team_name = _sanitize_text(team_name, "team_name")
            result = await stats.get_player_stats(team_query=team_name)
            return formatting.format_player_stats(result)
        except CBBError as e:
            return str(e)
        except Exception:
            logger.exception("unexpected_error", tool="get_player_stats")
            return "An unexpected error occurred. Please try again."


@mcp.tool()
async def get_stat_leaders(category: str = "scoring", season: int = 0) -> str:
    """Get national statistical leaders by category.

    Args:
        category: Stat category — "scoring", "rebounds", "assists", "steals",
                  "blocks", "field_goal_pct", "three_point_pct", "free_throw_pct"
        season: Season year. Defaults to current season.
    """
    async with _concurrency:
        try:
            category = _sanitize_text(category, "category")
            season = _validate_season(season)
            result = await stats.get_stat_leaders(category, season)
            return formatting.format_stat_leaders(result)
        except CBBError as e:
            return str(e)
        except Exception:
            logger.exception("unexpected_error", tool="get_stat_leaders")
            return "An unexpected error occurred. Please try again."


@mcp.tool()
async def compare_teams(team1: str, team2: str) -> str:
    """Compare two teams side-by-side with stats and advantages.

    Args:
        team1: First team name (fuzzy matched)
        team2: Second team name (fuzzy matched)
    """
    async with _concurrency:
        try:
            team1 = _sanitize_text(team1, "team1")
            team2 = _sanitize_text(team2, "team2")
            result = await stats.compare_teams(team1, team2)
            return formatting.format_comparison(result)
        except CBBError as e:
            return str(e)
        except Exception:
            logger.exception("unexpected_error", tool="compare_teams")
            return "An unexpected error occurred. Please try again."


# ═══════════════════════════════════════════════════════════════
# Calendar / Tournament
# ═══════════════════════════════════════════════════════════════

@mcp.tool()
async def get_games_by_date(date: str = "", conference: str = "") -> str:
    """Get all games on a specific date with TV broadcast info.

    Args:
        date: Date in YYYY-MM-DD format. Defaults to today.
        conference: Optional conference filter
    """
    async with _concurrency:
        try:
            d = _validate_date(date)
            if conference:
                conference = _sanitize_text(conference, "conference")
            result = await games.get_live_scores(d, conference)
            header = f"**Games on {d}**"
            if conference:
                header += f" ({conference})"
            lines = [header, ""]
            for g in result:
                line = formatting.format_game(g)
                if g.broadcast:
                    line += f"  [TV: {g.broadcast}]"
                lines.append(line)
            return "\n".join(lines) if len(lines) > 2 else f"No games scheduled for {d}."
        except CBBError as e:
            return str(e)
        except Exception:
            logger.exception("unexpected_error", tool="get_games_by_date")
            return "An unexpected error occurred. Please try again."


@mcp.tool()
async def get_tournament_bracket(season: int = 0) -> str:
    """Get March Madness tournament bracket and results.

    Args:
        season: Season year. Defaults to current season.
    """
    async with _concurrency:
        try:
            season = _validate_season(season) or CURRENT_SEASON
            d = f"{season}-03-18"
            result = await games.get_live_scores(d)
            tournament_games = [g for g in result if "ncaa" in g.notes.lower() or "tournament" in g.notes.lower()]
            if not tournament_games:
                tournament_games = result

            if not tournament_games:
                return f"No tournament data available for the {season} season yet. The NCAA Tournament typically begins in mid-March."

            lines = [f"**{season} NCAA Tournament**\n"]
            for g in tournament_games:
                lines.append(f"{g.notes or 'Tournament'}: {formatting.format_game(g)}")
            return "\n".join(lines)
        except CBBError as e:
            return str(e)
        except Exception:
            logger.exception("unexpected_error", tool="get_tournament_bracket")
            return "An unexpected error occurred. Please try again."


# ═══════════════════════════════════════════════════════════════
# Resources
# ═══════════════════════════════════════════════════════════════

@mcp.resource("cbb://conferences")
async def list_conferences() -> str:
    """List all NCAA D1 conferences."""
    lines = ["**NCAA D1 Conferences**\n"]
    for short, info in sorted(ESPN_CONFERENCES.items()):
        lines.append(f"  {short:<16} {info['name']}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Prompts
# ═══════════════════════════════════════════════════════════════

@mcp.prompt()
async def game_preview_prompt(team1: str, team2: str) -> str:
    """Generate a game preview analysis prompt for two teams.

    Args:
        team1: First team name
        team2: Second team name
    """
    return (
        f"Please provide a comprehensive game preview for {team1} vs {team2}. "
        f"Use the following tools to gather data:\n"
        f"1. get_team for both teams to get records and rankings\n"
        f"2. compare_teams to get a side-by-side statistical comparison\n"
        f"3. get_team_schedule for both teams to see recent results\n"
        f"4. get_rankings to see where they stand nationally\n\n"
        f"Then synthesize this data into a preview covering:\n"
        f"- Team records and rankings\n"
        f"- Key statistical matchups\n"
        f"- Recent form (last 5 games)\n"
        f"- Key players to watch\n"
        f"- Prediction with reasoning"
    )


@mcp.prompt()
async def season_recap_prompt(team_name: str) -> str:
    """Generate a season recap analysis prompt for a team.

    Args:
        team_name: Team name
    """
    return (
        f"Please provide a comprehensive season recap for {team_name}. "
        f"Use the following tools to gather data:\n"
        f"1. get_team to get the team's final record and conference\n"
        f"2. get_team_stats for their season statistics\n"
        f"3. get_player_stats for individual player performance\n"
        f"4. get_team_schedule to review their full schedule and results\n"
        f"5. get_standings to see their conference finish\n\n"
        f"Then synthesize this data into a recap covering:\n"
        f"- Overall season record and conference finish\n"
        f"- Key team statistics and where they ranked\n"
        f"- Top performers and breakout players\n"
        f"- Biggest wins and toughest losses\n"
        f"- Season highlights and defining moments"
    )


# ═══════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════

def main():
    """CLI entry point for cbb-mcp."""
    transport = settings.transport
    if len(sys.argv) > 1:
        transport = sys.argv[1]

    if transport == "streamable-http":
        import uvicorn

        app = mcp.streamable_http_app()

        # Timing-safe Bearer token auth middleware
        if settings.server_api_key:
            from starlette.middleware.base import BaseHTTPMiddleware
            from starlette.requests import Request
            from starlette.responses import JSONResponse

            async def auth_middleware(request: Request, call_next):
                auth = request.headers.get("authorization", "")
                token = auth[7:] if auth.startswith("Bearer ") else ""
                if not hmac.compare_digest(token, settings.server_api_key):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)
                return await call_next(request)

            app.add_middleware(BaseHTTPMiddleware, dispatch=auth_middleware)

        # Warn if API key auth is used without TLS on non-localhost
        if settings.server_api_key and settings.host != "127.0.0.1":
            logger.warning(
                "security_warning",
                message="API key auth is enabled on a non-localhost address. "
                        "Deploy behind a TLS-terminating reverse proxy (nginx, Caddy) "
                        "to protect credentials in transit.",
            )

        logger.info(
            "starting_http_server",
            host=settings.host,
            port=settings.port,
            auth="enabled" if settings.server_api_key else "disabled",
        )
        uvicorn.run(app, host=settings.host, port=settings.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

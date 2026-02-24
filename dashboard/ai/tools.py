"""
Tool definitions for Gemini function calling.
Dispatches to the MCP server via stdio (MCPClient).
"""

from __future__ import annotations

from typing import Any

# ── Gemini function declaration format ───────────────────────────────────────
# Each entry becomes a function_declaration in a Gemini Tool.

FUNCTION_DECLARATIONS: list[dict] = [
    {
        "name": "get_team",
        "description": "Look up a college basketball team by name (fuzzy matched). Returns team info including record, conference, and venue.",
        "parameters": {
            "type": "object",
            "properties": {
                "team_name": {"type": "string", "description": "Team name, abbreviation, or mascot (e.g. 'Duke', 'UNC', 'Wildcats')"},
            },
            "required": ["team_name"],
        },
    },
    {
        "name": "search_teams",
        "description": "Search for college basketball teams by name or conference.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (team name, city, abbreviation)"},
                "conference": {"type": "string", "description": "Optional conference filter (e.g. 'ACC', 'Big Ten', 'SEC')"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_team_roster",
        "description": "Get the full roster for a college basketball team.",
        "parameters": {
            "type": "object",
            "properties": {
                "team_name": {"type": "string", "description": "Team name (fuzzy matched)"},
            },
            "required": ["team_name"],
        },
    },
    {
        "name": "get_team_schedule",
        "description": "Get the complete schedule for a college basketball team, including results and upcoming games.",
        "parameters": {
            "type": "object",
            "properties": {
                "team_name": {"type": "string", "description": "Team name (fuzzy matched)"},
                "season": {"type": "integer", "description": "Season year (e.g. 2025). Defaults to current season."},
            },
            "required": ["team_name"],
        },
    },
    {
        "name": "get_live_scores",
        "description": "Get live and final college basketball scores for a given date.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format. Defaults to today."},
                "conference": {"type": "string", "description": "Optional conference filter (e.g. 'ACC', 'Big Ten')"},
                "top25_only": {"type": "boolean", "description": "If true, only show games involving ranked teams"},
            },
        },
    },
    {
        "name": "get_game_detail",
        "description": "Get comprehensive details for a specific game including scoring summary.",
        "parameters": {
            "type": "object",
            "properties": {
                "game_id": {"type": "string", "description": "ESPN game ID"},
            },
            "required": ["game_id"],
        },
    },
    {
        "name": "get_box_score",
        "description": "Get detailed per-player and team box score for a game.",
        "parameters": {
            "type": "object",
            "properties": {
                "game_id": {"type": "string", "description": "ESPN game ID"},
            },
            "required": ["game_id"],
        },
    },
    {
        "name": "get_play_by_play",
        "description": "Get play-by-play data for a game.",
        "parameters": {
            "type": "object",
            "properties": {
                "game_id": {"type": "string", "description": "ESPN game ID"},
                "last_n": {"type": "integer", "description": "Number of most recent plays to show (0 for all). Defaults to 20."},
            },
            "required": ["game_id"],
        },
    },
    {
        "name": "get_rankings",
        "description": "Get college basketball poll rankings (AP Top 25, Coaches Poll).",
        "parameters": {
            "type": "object",
            "properties": {
                "poll": {"type": "string", "description": "'ap' (default) or 'coaches'"},
                "season": {"type": "integer", "description": "Season year. Defaults to current season."},
                "week": {"type": "integer", "description": "Specific week. Defaults to latest."},
            },
        },
    },
    {
        "name": "get_standings",
        "description": "Get conference standings with records and streaks.",
        "parameters": {
            "type": "object",
            "properties": {
                "conference": {"type": "string", "description": "Conference name (e.g. 'ACC', 'Big Ten'). Leave empty for all conferences."},
            },
        },
    },
    {
        "name": "get_team_stats",
        "description": "Get season statistics for a team (PPG, FG%, rebounds, assists, etc.).",
        "parameters": {
            "type": "object",
            "properties": {
                "team_name": {"type": "string", "description": "Team name (fuzzy matched)"},
                "season": {"type": "integer", "description": "Season year. Defaults to current season."},
            },
            "required": ["team_name"],
        },
    },
    {
        "name": "get_player_stats",
        "description": "Get individual player season statistics for all players on a team.",
        "parameters": {
            "type": "object",
            "properties": {
                "team_name": {"type": "string", "description": "Team name (fuzzy matched)"},
            },
            "required": ["team_name"],
        },
    },
    {
        "name": "get_stat_leaders",
        "description": "Get national statistical leaders by category.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Stat category: 'scoring', 'rebounds', 'assists', 'steals', 'blocks', 'field_goal_pct', 'three_point_pct', 'free_throw_pct'",
                },
                "season": {"type": "integer", "description": "Season year. Defaults to current season."},
            },
        },
    },
    {
        "name": "compare_teams",
        "description": "Compare two teams side-by-side with stats and advantages.",
        "parameters": {
            "type": "object",
            "properties": {
                "team1": {"type": "string", "description": "First team name (fuzzy matched)"},
                "team2": {"type": "string", "description": "Second team name (fuzzy matched)"},
            },
            "required": ["team1", "team2"],
        },
    },
    {
        "name": "get_games_by_date",
        "description": "Get all games on a specific date with TV broadcast info.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format. Defaults to today."},
                "conference": {"type": "string", "description": "Optional conference filter"},
            },
        },
    },
    {
        "name": "get_tournament_bracket",
        "description": "Get March Madness tournament bracket and results.",
        "parameters": {
            "type": "object",
            "properties": {
                "season": {"type": "integer", "description": "Season year. Defaults to current season."},
            },
        },
    },
]


# ── Gemini Tool wrapper ───────────────────────────────────────────────────────

def get_gemini_tools() -> list[dict]:
    """Return the tool list in Gemini's expected format."""
    return [{"function_declarations": FUNCTION_DECLARATIONS}]


# ── MCP dispatch ─────────────────────────────────────────────────────────────

async def dispatch_tool(tool_name: str, tool_args: dict[str, Any]) -> str:
    """
    Dispatch a tool call to the MCP server via stdio.
    Returns the text result string.
    """
    from dashboard.ai.mcp_client import get_client

    client = get_client()
    return await client.call_tool(tool_name, tool_args)

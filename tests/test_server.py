"""Tests for the MCP server tool registrations."""

import pytest

from cbb_mcp.server import mcp


def test_server_has_tools():
    """Verify all 16 tools are registered."""
    # FastMCP stores tools internally; check the tool list
    tool_names = [tool.name for tool in mcp._tool_manager.list_tools()]
    expected_tools = [
        "get_team",
        "search_teams",
        "get_team_roster",
        "get_team_schedule",
        "get_live_scores",
        "get_game_detail",
        "get_box_score",
        "get_play_by_play",
        "get_rankings",
        "get_standings",
        "get_team_stats",
        "get_player_stats",
        "get_stat_leaders",
        "compare_teams",
        "get_games_by_date",
        "get_tournament_bracket",
    ]
    for tool in expected_tools:
        assert tool in tool_names, f"Missing tool: {tool}"


def test_server_name():
    assert mcp.name == "College Basketball"

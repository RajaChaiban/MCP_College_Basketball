"""
Game panel callbacks: map click → open offcanvas, load box score / PBP.
"""

from __future__ import annotations

from dash import Input, Output, State, callback, no_update

from dashboard.components.game_panel import build_game_panel_content
from dashboard.utils import run_async


def register_game_callbacks(app) -> None:
    """Register game panel callbacks."""

    @app.callback(
        Output("game-panel", "is_open"),
        Output("game-panel", "children"),
        Output("selected-game-store", "data"),
        Input("us-map", "clickData"),
        State("game-panel", "is_open"),
        prevent_initial_call=True,
    )
    def open_game_panel(click_data, is_open):
        """Open the game panel when a map marker is clicked."""
        if not click_data:
            return no_update, no_update, no_update

        points = click_data.get("points", [])
        if not points:
            return no_update, no_update, no_update

        # game_id is stored in customdata
        game_id = points[0].get("customdata")
        if not game_id:
            return no_update, no_update, no_update

        game, box_score, pbp = _fetch_game_data(game_id)
        panel_content = build_game_panel_content(game, box_score, pbp)

        return True, panel_content, {"game_id": game_id}

    @app.callback(
        Output("game-panel", "children", allow_duplicate=True),
        Input("live-refresh", "n_intervals"),
        State("selected-game-store", "data"),
        State("game-panel", "is_open"),
        prevent_initial_call=True,
    )
    def refresh_game_panel(n_intervals, selected_game, is_open):
        """Re-fetch box score for the open panel if game is live."""
        if not is_open or not selected_game:
            return no_update

        game_id = selected_game.get("game_id")
        if not game_id:
            return no_update

        game, box_score, pbp = _fetch_game_data(game_id)

        # Only refresh if game is live
        if not game or game.status != "in":
            return no_update

        return build_game_panel_content(game, box_score, pbp)

    @app.callback(
        Output("chat-panel", "is_open"),
        Input("ask-ai-btn", "n_clicks"),
        State("chat-panel", "is_open"),
        prevent_initial_call=True,
    )
    def open_chat_from_game(n_clicks, is_open):
        """Open chat panel when 'Ask AI' button is clicked."""
        if n_clicks:
            return True
        return is_open


def _fetch_game_data(game_id: str):
    """Fetch game, box score, and PBP concurrently."""
    from cbb_mcp.services import games as games_svc
    import asyncio

    async def _fetch_all():
        tasks = await asyncio.gather(
            games_svc.get_game_detail(game_id),
            games_svc.get_box_score(game_id),
            games_svc.get_play_by_play(game_id),
            return_exceptions=True,
        )
        return tasks

    results = run_async(_fetch_all())
    game = results[0] if not isinstance(results[0], Exception) else None
    box_score = results[1] if not isinstance(results[1], Exception) else None
    pbp = results[2] if not isinstance(results[2], Exception) else None
    return game, box_score, pbp

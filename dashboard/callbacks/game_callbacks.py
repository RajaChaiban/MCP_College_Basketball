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
        State("prob-history-store", "data"),
        prevent_initial_call=True,
    )
    def open_game_panel(click_data, is_open, history_data):
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

        history = (history_data or {}).get(game_id, [])

        pre_game_prob = None
        if game and getattr(game, "status", "in") == "pre":
            from dashboard.ai.predictor import get_win_probability
            pre_game_prob = get_win_probability(game)

        panel_content = build_game_panel_content(game, box_score, pbp, history, win_prob=pre_game_prob)

        return True, panel_content, {"game_id": game_id}

    def _format_game_time(game: object) -> tuple[str, int]:
        """Calculate elapsed time from start of game (e.g., '1:30', '25:45', '40:00')."""
        try:
            period = getattr(game, "period", 1) or 1
            clock = getattr(game, "clock", "20:00") or "20:00"

            # Parse clock (remaining time in current period)
            try:
                parts = str(clock).split(":")
                mins_remaining = int(parts[0])
                secs_remaining = int(parts[1]) if len(parts) > 1 else 0
            except:
                return "0:00", 0

            # Each quarter is 20 minutes (1200 seconds)
            quarter_duration = 20 * 60

            # Calculate total seconds remaining in current period
            total_secs_remaining = mins_remaining * 60 + secs_remaining

            # Calculate elapsed time based on period
            if period <= 2:
                # Regular quarters: 1-2
                # Elapsed = (periods passed * 20min) + (20min - remaining)
                elapsed_secs = (period - 1) * quarter_duration + (quarter_duration - total_secs_remaining)
            else:
                # Overtime (5 minutes each)
                elapsed_secs = 2 * quarter_duration  # First 2 quarters (40 minutes)
                ot_num = period - 2  # Which OT we're in (1, 2, 3, etc.)
                ot_duration = 5 * 60  # 5 minutes per OT (300 seconds)
                elapsed_secs += (ot_num - 1) * ot_duration + (ot_duration - total_secs_remaining)

            # Convert back to MM:SS
            mins_elapsed = elapsed_secs // 60
            secs_elapsed = elapsed_secs % 60

            return f"{mins_elapsed}:{secs_elapsed:02d}", elapsed_secs
        except Exception as e:
            print(f"[elapsed_time_format] Error: {e}")
            return "0:00", 0

    @app.callback(
        Output("game-panel", "children", allow_duplicate=True),
        Output("prob-history-store", "data", allow_duplicate=True),
        Input("live-refresh", "n_intervals"),
        State("selected-game-store", "data"),
        State("game-panel", "is_open"),
        State("prob-history-store", "data"),
        prevent_initial_call=True,
    )
    def refresh_game_panel(n_intervals, selected_game, is_open, history_data):
        """Re-fetch box score for the open panel if game is live."""
        if not is_open or not selected_game:
            return no_update, no_update

        game_id = selected_game.get("game_id")
        if not game_id:
            return no_update, no_update

        game, box_score, pbp = _fetch_game_data(game_id)

        # Only refresh if game is live
        if not game or game.status != "in":
            return no_update, no_update

        # Re-calculate win prob with fresh PBP
        from dashboard.ai.predictor import get_win_probability

        prob = get_win_probability(game, pbp=pbp)

        history = history_data or {}
        if not isinstance(history, dict):
            history = {}

        # Update history for this game
        if prob is not None:
            game_id_str = str(game_id)
            if game_id_str not in history:
                history[game_id_str] = []

            # Extract game time instead of clock time
            game_time_str, game_time_secs = _format_game_time(game)
            history[game_id_str].append({"time_str": game_time_str, "time_secs": game_time_secs, "prob": float(prob)})

            # Keep history size reasonable (max 200 data points)
            if len(history[game_id_str]) > 200:
                history[game_id_str].pop(0)

        current_history = history.get(str(game_id), [])
        panel_content = build_game_panel_content(game, box_score, pbp, current_history, win_prob=prob)
        return panel_content, history

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

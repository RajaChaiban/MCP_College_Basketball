"""
Map callbacks: interval → fetch live scores → rebuild map figure.
"""

from __future__ import annotations

from datetime import date

from dash import Input, Output, State, callback, no_update

from dashboard.components.map_view import build_map_figure, build_empty_map
from dashboard.utils import run_async


def _get_elapsed_seconds(game) -> int:
    """Calculate total elapsed seconds from start of game (0 to 2400+)."""
    try:
        period = getattr(game, "period", 1) or 1
        clock = getattr(game, "clock", "20:00") or "20:00"

        # Parse clock (remaining time in current period)
        try:
            parts = str(clock).split(":")
            mins_remaining = int(parts[0])
            secs_remaining = int(parts[1]) if len(parts) > 1 else 0
        except:
            return 0

        # Each half is 20 minutes (1200 seconds)
        half_duration = 20 * 60
        total_secs_remaining = mins_remaining * 60 + secs_remaining

        if period <= 2:
            return (period - 1) * half_duration + (half_duration - total_secs_remaining)
        else:
            # Overtime (5 minutes each)
            ot_num = period - 2
            ot_duration = 5 * 60
            return (2 * half_duration) + (ot_num - 1) * ot_duration + (ot_duration - total_secs_remaining)
    except:
        return 0

def _format_game_time(game) -> str:
    """Return friendly MM:SS string of elapsed time."""
    seconds = _get_elapsed_seconds(game)
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins}:{secs:02d}"


def register_map_callbacks(app) -> None:
    """Register all map-related callbacks."""

    @app.callback(
        Output("us-map", "figure"),
        Output("games-store", "data"),
        Output("prob-history-store", "data"),
        Input("live-refresh", "n_intervals"),
        Input("conference-filter", "value"),
        State("prob-history-store", "data"),
        prevent_initial_call=False,
    )
    def refresh_map(n_intervals, conference, history_data):
        """Fetch live scores and rebuild the map on every interval tick."""
        from cbb_mcp.services import games as games_svc
        from dashboard.ai.predictor import get_win_probability
        from datetime import date, timedelta, datetime

        today_dt = date.today()
        yesterday_dt = today_dt - timedelta(days=1)
        
        today = today_dt.isoformat()
        yesterday = yesterday_dt.isoformat()
        
        conf = conference or ""
        history = history_data or {}

        try:
            # Fetch both days to catch games that started before midnight but are still live
            today_games = run_async(
                games_svc.get_live_scores(date=today, conference=conf, top25=False)
            )
            yesterday_games = run_async(
                games_svc.get_live_scores(date=yesterday, conference=conf, top25=False)
            )
            
            # Merge and deduplicate by ID
            merged_games = {g.id: g for g in (yesterday_games + today_games)}
            games = list(merged_games.values())
            
        except Exception as e:
            print(f"[map] Error fetching scores: {e}")
            return build_empty_map(), [], history

        if not games:
            return build_empty_map(), [], history

        # Serialize games and calculate win probability
        games_data = []

        # history is a dict of game_id -> list of snapshots
        if not isinstance(history, dict):
            history = {}

        for g in games:
            prob = get_win_probability(g)
            g_dict = g.model_dump()
            g_dict["win_prob"] = prob
            games_data.append(g_dict)

            # Store in history
            if g.status == "in":
                game_id = str(g.id)
                if game_id not in history:
                    history[game_id] = []
                # Only append if prob is not None
                if prob is not None:
                    # Extract game time
                    elapsed_secs = _get_elapsed_seconds(g)
                    game_time_str = _format_game_time(g)
                    
                    # Limit history size to 200 snapshots
                    history[game_id].append({
                        "time_secs": elapsed_secs, 
                        "time_str": game_time_str, 
                        "prob": float(prob)
                    })
                    if len(history[game_id]) > 200:
                        history[game_id].pop(0)

        fig = build_map_figure(games_data, conference_filter=conf)

        return fig, games_data, history

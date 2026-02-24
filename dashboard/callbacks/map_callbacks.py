"""
Map callbacks: interval → fetch live scores → rebuild map figure.
"""

from __future__ import annotations

from datetime import date

from dash import Input, Output, State, callback, no_update

from dashboard.components.map_view import build_map_figure, build_empty_map
from dashboard.utils import run_async


def register_map_callbacks(app) -> None:
    """Register all map-related callbacks."""

    @app.callback(
        Output("us-map", "figure"),
        Output("games-store", "data"),
        Input("live-refresh", "n_intervals"),
        Input("conference-filter", "value"),
        prevent_initial_call=False,
    )
    def refresh_map(n_intervals, conference):
        """Fetch live scores and rebuild the map on every interval tick."""
        from cbb_mcp.services import games as games_svc

        today = date.today().isoformat()
        conf = conference or ""

        try:
            games = run_async(
                games_svc.get_live_scores(date=today, conference=conf, top25=False)
            )
        except Exception as e:
            print(f"[map] Error fetching scores: {e}")
            return build_empty_map(), []

        if not games:
            return build_empty_map(), []

        fig = build_map_figure(games, conference_filter=conf)

        # Serialize games to dicts for the store
        games_data = []
        for g in games:
            try:
                games_data.append(g.model_dump())
            except Exception:
                pass

        return fig, games_data

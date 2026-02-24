"""
Rankings callbacks: refresh AP Top 25 + all teams sidebar.
"""

from __future__ import annotations

from dash import Input, Output, State, callback, clientside_callback, no_update

from dashboard.components.rankings_sidebar import build_rankings_list, build_all_teams_section
from dashboard.utils import run_async


def register_rankings_callbacks(app) -> None:
    """Register rankings sidebar callbacks."""

    @app.callback(
        Output("rankings-content", "children"),
        Input("rankings-refresh", "n_intervals"),
        prevent_initial_call=False,
    )
    def refresh_rankings(n_intervals):
        """Fetch AP Top 25 rankings."""
        from cbb_mcp.services import rankings as rankings_svc

        try:
            poll = run_async(rankings_svc.get_rankings(poll_type="ap"))
            return build_rankings_list(poll, poll_type="ap")
        except Exception as e:
            print(f"[rankings] Error: {e}")
            return build_rankings_list(None, poll_type="ap")

    @app.callback(
        Output("all-teams-content", "children"),
        Input("rankings-refresh", "n_intervals"),
        prevent_initial_call=False,
    )
    def refresh_all_teams(n_intervals):
        """Fetch all D1 teams."""
        from cbb_mcp.services import teams as teams_svc

        try:
            all_teams = run_async(teams_svc.search_teams(""))
            return build_all_teams_section(all_teams)
        except Exception as e:
            print(f"[all-teams] Error: {e}")
            return build_all_teams_section(None)

    # Client-side search filter — instant, no round-trip
    app.clientside_callback(
        """
        function(search, _) {
            var query = (search || "").toLowerCase().trim();
            var rows = document.querySelectorAll("#all-teams-list .team-row");
            var headers = document.querySelectorAll("#all-teams-list .team-conference-header");

            rows.forEach(function(row) {
                var name = (row.getAttribute("data-team-name") || "").toLowerCase();
                row.style.display = (!query || name.includes(query)) ? "" : "none";
            });

            // Hide conference headers if all their teams are hidden
            headers.forEach(function(header) {
                var next = header.nextElementSibling;
                var anyVisible = false;
                while (next && next.classList.contains("team-row")) {
                    if (next.style.display !== "none") { anyVisible = true; break; }
                    next = next.nextElementSibling;
                }
                header.style.display = anyVisible ? "" : "none";
            });

            return window.dash_clientside.no_update;
        }
        """,
        Output("all-teams-list", "data-search"),
        Input("team-search-input", "value"),
        Input("all-teams-content", "children"),
    )

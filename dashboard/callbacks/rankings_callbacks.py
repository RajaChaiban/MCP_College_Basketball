"""
Rankings callbacks: refresh AP Top 25 + all teams sidebar.
"""

from __future__ import annotations

from dash import Input, Output, State, callback, clientside_callback, no_update

from dashboard.components.rankings_sidebar import build_rankings_list, build_all_teams_rows
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
        try:
            from cbb_mcp.services import rankings as rankings_svc
            poll = run_async(rankings_svc.get_rankings(poll_type="ap"))
            return build_rankings_list(poll, poll_type="ap")
        except Exception as e:
            print(f"[rankings] Error: {e}")
            return build_rankings_list(None, poll_type="ap")

    @app.callback(
        Output("all-teams-list", "children"),
        Input("rankings-refresh", "n_intervals"),
        prevent_initial_call=False,
    )
    def refresh_all_teams(n_intervals):
        """Fetch all D1 teams and enrich with current AP Top 25 rankings."""
        from cbb_mcp.services import teams as teams_svc, rankings as rankings_svc

        try:
            all_teams = run_async(teams_svc.search_teams(""))

            # Enrich teams with current AP Top 25 rankings
            try:
                poll = run_async(rankings_svc.get_rankings(poll_type="ap"))
                # Build maps of team name -> rank and team ID -> rank
                rankings_by_name: dict[str, int] = {}
                rankings_by_id: dict[str, int] = {}
                if poll and hasattr(poll, 'teams'):
                    for ranked_team in poll.teams:
                        name = ranked_team.team_name.lower() if ranked_team.team_name else ""
                        team_id = str(ranked_team.team_id) if ranked_team.team_id else ""
                        if name:
                            rankings_by_name[name] = ranked_team.rank
                        if team_id:
                            rankings_by_id[team_id] = ranked_team.rank

                # Enrich teams with ranks from current rankings
                for team in all_teams:
                    team_name_lower = team.name.lower() if team.name else ""
                    team_id = str(team.id) if team.id else ""
                    # Try matching by name first, then by ID
                    if team_name_lower in rankings_by_name:
                        team.rank = rankings_by_name[team_name_lower]
                    elif team_id in rankings_by_id:
                        team.rank = rankings_by_id[team_id]
            except Exception as e:
                print(f"[all-teams] Ranking enrichment failed: {e}")
                # Continue without enrichment if rankings fail

            return build_all_teams_rows(all_teams)
        except Exception as e:
            print(f"[all-teams] Error: {e}")
            return build_all_teams_rows(None)

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
        Input("all-teams-list", "children"),
    )

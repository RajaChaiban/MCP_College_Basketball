"""
Rankings sidebar: AP Top 25 + all D1 teams with search.
"""

from __future__ import annotations

from dash import html, dcc
import dash_bootstrap_components as dbc


def build_rankings_list(poll: object | None, poll_type: str = "ap") -> html.Div:
    """
    Build the AP Top 25 ranked teams section.

    Args:
        poll: Poll model instance (or None if not loaded).
        poll_type: "ap" or "coaches".

    Returns:
        html.Div with ranked teams list.
    """
    title = "AP Top 25" if poll_type == "ap" else "Coaches Poll"

    if poll is None:
        return html.Div([
            html.H6(title, className="rankings-title"),
            html.P("Loading rankings...", className="text-muted small"),
        ])

    entries = getattr(poll, "teams", None) or getattr(poll, "rankings", None) or []

    if not entries:
        return html.Div([
            html.H6(title, className="rankings-title"),
            html.P("Rankings not available", className="text-muted small"),
        ])

    rows = []
    for entry in entries[:25]:
        rank = getattr(entry, "rank", "?")
        team_name = getattr(entry, "team_name", "Unknown")
        record = getattr(entry, "record", "")
        prev_rank = getattr(entry, "previous_rank", None)

        if prev_rank and prev_rank != rank:
            diff = prev_rank - rank
            if diff > 0:
                change = html.Span(f"▲{diff}", className="rank-up")
            else:
                change = html.Span(f"▼{abs(diff)}", className="rank-down")
        else:
            change = html.Span("—", className="rank-same")

        row = html.Div(
            [
                html.Span(f"{rank}", className="rank-number"),
                html.Span(team_name, className="rank-team-name"),
                html.Span(record, className="rank-record"),
                change,
            ],
            className="rank-row",
        )
        rows.append(row)

    week_label = f"Week {poll.week}" if hasattr(poll, "week") and poll.week else "Current"

    return html.Div(
        [
            html.Div(
                [
                    html.H6(title, className="rankings-title"),
                    html.Span(week_label, className="rankings-week"),
                ],
                className="rankings-header",
            ),
            html.Div(rows, className="rankings-list"),
        ]
    )


def build_all_teams_section(all_teams: list | None) -> html.Div:
    """
    Build the all-teams section with search box.

    Args:
        all_teams: List of Team objects (or None if not loaded).

    Returns:
        html.Div with search input + scrollable team list.
    """
    if not all_teams:
        return html.Div([
            html.H6("All Teams", className="rankings-title mt-3"),
            html.P("Loading teams...", className="text-muted small"),
        ])

    # Group by conference, sort alphabetically within each group
    conferences: dict[str, list] = {}
    for team in all_teams:
        conf = getattr(team, "conference", "") or "Independent"
        if not conf:
            conf = "Independent"
        conferences.setdefault(conf, []).append(team)

    for conf in conferences:
        conferences[conf].sort(key=lambda t: getattr(t, "name", ""))

    sorted_confs = sorted(conferences.keys())

    rows = []
    for conf in sorted_confs:
        # Conference header
        rows.append(
            html.Div(conf, className="team-conference-header")
        )
        for team in conferences[conf]:
            name = getattr(team, "name", "Unknown")
            record = getattr(team, "record", None)
            rank = getattr(team, "rank", None)
            wins = getattr(record, "wins", 0) if record else 0
            losses = getattr(record, "losses", 0) if record else 0
            record_str = f"{wins}-{losses}" if (wins or losses) else ""

            rank_badge = (
                html.Span(f"#{rank}", className="team-rank-badge")
                if rank else html.Span("", className="team-rank-badge-empty")
            )

            rows.append(
                html.Div(
                    [
                        rank_badge,
                        html.Span(name, className="team-name-text"),
                        html.Span(record_str, className="team-record-text"),
                    ],
                    className="team-row ranked-team-row" if rank else "team-row",
                    **{"data-team-name": name.lower()},
                )
            )

    return html.Div(
        [
            html.H6("All Teams", className="rankings-title mt-3"),
            dcc.Input(
                id="team-search-input",
                type="text",
                placeholder="Search teams...",
                debounce=True,
                className="team-search-input",
            ),
            html.Div(rows, id="all-teams-list", className="all-teams-list"),
        ]
    )


def build_rankings_sidebar(poll_ap: object | None = None, all_teams: list | None = None) -> dbc.Card:
    """Wrap rankings + all-teams in a styled card."""
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.Div(
                        build_rankings_list(poll_ap, poll_type="ap"),
                        id="rankings-content",
                    ),
                    html.Hr(className="rankings-divider"),
                    html.Div(
                        build_all_teams_section(all_teams),
                        id="all-teams-content",
                    ),
                ],
                className="rankings-card-body",
            )
        ],
        className="rankings-card",
    )

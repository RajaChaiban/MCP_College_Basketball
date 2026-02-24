"""
Top-level dashboard layout: map + rankings sidebar + offcanvas panels + stores.
"""

from __future__ import annotations

from dash import dcc, html
import dash_bootstrap_components as dbc

from dashboard.components.chat_panel import build_chat_panel
from dashboard.components.map_view import build_empty_map
from dashboard.components.rankings_sidebar import build_rankings_sidebar

# ESPN conference filter options
CONFERENCE_OPTIONS = [
    {"label": "All Conferences", "value": ""},
    {"label": "ACC", "value": "ACC"},
    {"label": "Big Ten", "value": "Big Ten"},
    {"label": "Big 12", "value": "Big 12"},
    {"label": "SEC", "value": "SEC"},
    {"label": "Big East", "value": "Big East"},
    {"label": "Pac-12", "value": "Pac-12"},
    {"label": "American Athletic", "value": "American Athletic"},
    {"label": "Mountain West", "value": "Mountain West"},
    {"label": "Atlantic 10", "value": "Atlantic 10"},
    {"label": "WCC", "value": "WCC"},
    {"label": "Missouri Valley", "value": "Missouri Valley"},
    {"label": "MAC", "value": "MAC"},
]


def build_layout() -> dbc.Container:
    """Build the full dashboard layout."""
    return dbc.Container(
        fluid=True,
        className="dashboard-container",
        children=[
            # ── Data stores ──────────────────────────────────────────────────
            dcc.Store(id="games-store", storage_type="memory"),
            dcc.Store(id="selected-game-store", storage_type="memory"),
            dcc.Store(id="conversation-store", storage_type="session"),

            # ── Intervals ────────────────────────────────────────────────────
            dcc.Interval(id="live-refresh", interval=30_000, n_intervals=0),
            dcc.Interval(id="rankings-refresh", interval=3_600_000, n_intervals=0),

            # ── Top bar ───────────────────────────────────────────────────────
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Span("CBB", className="logo-cbb"),
                                html.Span(" Live", className="logo-live"),
                            ],
                            className="top-bar-logo",
                        ),
                        width="auto",
                    ),
                    dbc.Col(
                        html.H6(
                            id="top-bar-date",
                            className="top-bar-date",
                            children=_get_date_str(),
                        ),
                        width="auto",
                        className="d-flex align-items-center",
                    ),
                    dbc.Col(
                        dcc.Dropdown(
                            id="conference-filter",
                            options=CONFERENCE_OPTIONS,
                            value="",
                            clearable=False,
                            className="conference-dropdown",
                            placeholder="All Conferences",
                        ),
                        width=2,
                        className="d-flex align-items-center",
                    ),
                    dbc.Col(
                        dbc.Button(
                            [html.I(className="fas fa-comment-dots me-2"), "AI Chat"],
                            id="open-chat-btn",
                            color="danger", # ESPN Red
                            size="sm",
                            className="ms-auto",
                            n_clicks=0,
                        ),
                        width="auto",
                        className="d-flex align-items-center ms-auto",
                    ),
                ],
                className="top-bar g-2",
                align="center",
            ),

            # ── Main content ─────────────────────────────────────────────────
            dbc.Row(
                [
                    # Map column
                    dbc.Col(
                        html.Div(
                            [
                                dcc.Graph(
                                    id="us-map",
                                    figure=build_empty_map(),
                                    config={
                                        "displayModeBar": False,
                                        "scrollZoom": True,
                                    },
                                    className="map-graph",
                                    style={"height": "calc(100vh - 80px)"},
                                ),
                                html.Div(
                                    id="game-count-badge",
                                    className="game-count-badge",
                                ),
                            ],
                            className="map-container",
                        ),
                        width=9,
                        className="map-col",
                    ),

                    # Rankings sidebar
                    dbc.Col(
                        build_rankings_sidebar(),
                        width=3,
                        className="rankings-col",
                    ),
                ],
                className="g-0 main-row",
            ),

            # ── Game offcanvas panel ──────────────────────────────────────────
            dbc.Offcanvas(
                id="game-panel",
                title="Game Details",
                placement="bottom",
                is_open=False,
                className="game-offcanvas",
                style={"height": "55vh"},
                children=[
                    html.P(
                        "Click a game marker on the map to view details.",
                        className="text-muted",
                    )
                ],
            ),

            # ── Chat offcanvas panel ──────────────────────────────────────────
            dbc.Offcanvas(
                id="chat-panel",
                title=html.Div(
                    [
                        html.Span("AI ANALYST"),
                        dbc.Button(
                            html.I(className="fas fa-times"),
                            id="close-chat-btn",
                            color="link",
                            size="sm",
                            className="ms-auto close-chat-btn",
                            n_clicks=0,
                        ),
                    ],
                    className="chat-panel-title",
                ),
                placement="end",
                is_open=False,
                className="chat-offcanvas",
                children=build_chat_panel(),
            ),
        ],
    )


def _get_date_str() -> str:
    from datetime import date
    return date.today().strftime("%A, %B %d, %Y")


# ── Open chat panel from top bar button ──────────────────────────────────────
def register_layout_callbacks(app) -> None:
    from dash import Input, Output, State, no_update

    @app.callback(
        Output("chat-panel", "is_open", allow_duplicate=True),
        Input("open-chat-btn", "n_clicks"),
        State("chat-panel", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_chat_from_topbar(n_clicks, is_open):
        if n_clicks:
            return not is_open
        return no_update

    @app.callback(
        Output("game-count-badge", "children"),
        Input("games-store", "data"),
    )
    def update_game_count(games_data):
        if not games_data:
            return ""
        total = len(games_data)
        live = sum(1 for g in games_data if g.get("status") == "in")
        if live:
            return [
                dbc.Badge(f"{live} LIVE", color="success", className="me-2"),
                dbc.Badge(f"{total} Total", color="secondary"),
            ]
        return dbc.Badge(f"{total} Games", color="secondary")

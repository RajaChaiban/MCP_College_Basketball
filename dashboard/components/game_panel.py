"""
Game panel components: score header, box score table, play-by-play list.
"""

from __future__ import annotations

from dash import html, dash_table
import dash_bootstrap_components as dbc


def build_score_header(game: object) -> html.Div:
    """Build the live score header for the game panel."""
    if not game:
        return html.Div()

    home = game.home
    away = game.away
    status = game.status or "pre"

    # Status badge
    if status == "in":
        status_text = game.status_detail or game.clock or "In Progress"
        badge_color = "success"
    elif status == "post":
        status_text = "Final"
        badge_color = "secondary"
    else:
        status_text = game.status_detail or "Upcoming"
        badge_color = "primary"

    def team_score_block(team, is_winner: bool) -> html.Div:
        rank_badge = (
            html.Span(f"#{team.rank}", className="team-rank-badge")
            if team.rank
            else None
        )
        winner_class = "score-winner" if is_winner and status == "post" else ""
        return html.Div(
            [
                html.Div(
                    [rank_badge, html.Span(team.team_name, className="team-name-score")],
                    className="team-name-row",
                ),
                html.Span(str(team.score), className=f"score-number {winner_class}"),
                html.Span(team.record, className="team-record-score"),
            ],
            className="team-score-block",
        )

    away_winner = status == "post" and away.score > home.score
    home_winner = status == "post" and home.score > away.score

    header = html.Div(
        [
            html.Div(
                [
                    team_score_block(away, away_winner),
                    html.Div(
                        [
                            dbc.Badge(status_text, color=badge_color, className="status-badge"),
                            html.Div("@", className="at-symbol"),
                        ],
                        className="score-separator",
                    ),
                    team_score_block(home, home_winner),
                ],
                className="score-row",
            ),
            html.Div(
                [
                    html.Span(game.venue or "", className="venue-text"),
                    html.Span(" | ", className="text-muted") if game.broadcast else None,
                    html.Span(game.broadcast or "", className="broadcast-text"),
                ],
                className="game-meta",
            ),
        ],
        className="score-header",
    )
    return header


def build_box_score(box_score: object) -> html.Div:
    """Build box score tables for both teams."""
    if not box_score:
        return html.P("Box score not available.", className="text-muted")

    def build_team_table(team_box) -> html.Div:
        columns = [
            {"name": "Player", "id": "name"},
            {"name": "MIN", "id": "minutes"},
            {"name": "PTS", "id": "points"},
            {"name": "REB", "id": "rebounds"},
            {"name": "AST", "id": "assists"},
            {"name": "STL", "id": "steals"},
            {"name": "BLK", "id": "blocks"},
            {"name": "TO", "id": "turnovers"},
            {"name": "FG", "id": "fg"},
            {"name": "3P", "id": "tp"},
            {"name": "FT", "id": "ft"},
        ]

        rows = []
        for p in team_box.players:
            if not p.name:
                continue
            rows.append({
                "name": p.name,
                "minutes": p.minutes or "DNP",
                "points": p.points,
                "rebounds": p.rebounds,
                "assists": p.assists,
                "steals": p.steals,
                "blocks": p.blocks,
                "turnovers": p.turnovers,
                "fg": f"{p.fgm}/{p.fga}",
                "tp": f"{p.tpm}/{p.tpa}",
                "ft": f"{p.ftm}/{p.fta}",
            })

        # Totals row
        t = team_box.totals
        if t:
            rows.append({
                "name": "TOTALS",
                "minutes": "—",
                "points": t.points,
                "rebounds": t.rebounds,
                "assists": t.assists,
                "steals": t.steals,
                "blocks": t.blocks,
                "turnovers": t.turnovers,
                "fg": f"{t.fgm}/{t.fga}",
                "tp": f"{t.tpm}/{t.tpa}",
                "ft": f"{t.ftm}/{t.fta}",
            })

        return html.Div(
            [
                html.H6(team_box.team_name, className="box-score-team-name"),
                dash_table.DataTable(
                    data=rows,
                    columns=columns,
                    style_table={"overflowX": "auto", "fontSize": "12px"},
                    style_header={
                        "backgroundColor": "#000000",
                        "color": "#FFFFFF",
                        "fontWeight": "bold",
                        "border": "1px solid #333333",
                        "textAlign": "center",
                    },
                    style_cell={
                        "backgroundColor": "#000000",
                        "color": "#A5A5A5",
                        "border": "1px solid #1A1A1A",
                        "textAlign": "center",
                        "padding": "4px 8px",
                        "minWidth": "40px",
                    },
                    style_cell_conditional=[
                        {"if": {"column_id": "name"}, "textAlign": "left", "minWidth": "120px", "color": "#FFFFFF"},
                    ],
                    style_data_conditional=[
                        {
                            "if": {"filter_query": '{name} = "TOTALS"'},
                            "backgroundColor": "#1A1A1A",
                            "color": "#FFFFFF",
                            "fontWeight": "bold",
                            "borderTop": "2px solid #CC0000",
                        },
                    ],
                    page_action="none",
                    sort_action="native",
                ),
            ],
            className="team-box-score",
        )

    return html.Div(
        [
            build_team_table(box_score.away),
            html.Hr(className="box-score-divider"),
            build_team_table(box_score.home),
        ],
        className="box-score-container",
    )


def build_pbp(pbp: object) -> html.Div:
    """Build play-by-play list."""
    if not pbp or not pbp.plays:
        return html.P("Play-by-play not available.", className="text-muted")

    plays = pbp.plays[-30:] if len(pbp.plays) > 30 else pbp.plays
    # Most recent first
    plays = list(reversed(plays))

    items = []
    for play in plays:
        score_str = f"{play.score_away}–{play.score_home}" if play.scoring_play else ""
        period_str = f"H{play.period}" if play.period <= 2 else f"OT{play.period - 2}"
        scoring_class = "pbp-scoring" if play.scoring_play else ""

        items.append(
            html.Div(
                [
                    html.Span(f"{period_str} {play.clock}", className="pbp-time"),
                    html.Span(play.description, className=f"pbp-desc {scoring_class}"),
                    html.Span(score_str, className="pbp-score") if score_str else None,
                ],
                className="pbp-row",
            )
        )

    return html.Div(items, className="pbp-container")


def build_game_panel_content(
    game: object | None,
    box_score: object | None,
    pbp: object | None,
) -> list:
    """Build the full game panel content (score header + tabs)."""
    if not game:
        return [html.P("Select a game on the map to view details.", className="text-muted")]

    score_header = build_score_header(game)

    tabs = dbc.Tabs(
        [
            dbc.Tab(
                build_box_score(box_score),
                label="Box Score",
                tab_id="tab-box",
                className="panel-tab",
            ),
            dbc.Tab(
                build_pbp(pbp),
                label="Play-by-Play",
                tab_id="tab-pbp",
                className="panel-tab",
            ),
        ],
        id="game-tabs",
        active_tab="tab-box",
        className="game-panel-tabs",
    )

    ask_ai_btn = dbc.Button(
        "Ask AI about this game",
        id="ask-ai-btn",
        color="primary",
        size="sm",
        outline=True,
        className="ask-ai-btn",
    )

    return [score_header, ask_ai_btn, html.Hr(className="panel-divider"), tabs]

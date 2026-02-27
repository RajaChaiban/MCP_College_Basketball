"""
Game panel components: score header, box score table, play-by-play list.
"""

from __future__ import annotations

from dash import html, dash_table, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go


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


def build_pre_game_analysis(game, win_prob: float | None) -> html.Div:
    """Build a pre-game analysis panel showing predicted winner, probability bars, and key factors."""
    home = game.home
    away = game.away

    if win_prob is None:
        home_prob = 0.5
    else:
        home_prob = float(win_prob)
    away_prob = 1.0 - home_prob

    # Determine predicted winner and confidence label
    if home_prob >= 0.5:
        winner_name = home.team_name
        conf_pct = home_prob
    else:
        winner_name = away.team_name
        conf_pct = away_prob

    if conf_pct >= 0.75:
        confidence_label = "Heavy Favorite"
    elif conf_pct >= 0.63:
        confidence_label = "Moderate Favorite"
    elif conf_pct >= 0.55:
        confidence_label = "Slight Favorite"
    else:
        confidence_label = "Even Matchup"

    h_rank = getattr(home, "rank", None)
    a_rank = getattr(away, "rank", None)
    h_record = getattr(home, "record", "N/A") or "N/A"
    a_record = getattr(away, "record", "N/A") or "N/A"
    is_neutral = getattr(game, "neutral_site", False)
    location_text = "Neutral Site" if is_neutral else f"{home.team_name} (Home)"

    return html.Div(
        [
            html.Div("Pre-Game Analysis", className="prediction-section-header"),

            # Predicted winner banner
            html.Div(
                [
                    html.Div("Predicted Winner", className="predicted-winner-label"),
                    html.Div(winner_name, className="predicted-winner-name"),
                    html.Div(f"{confidence_label} · {conf_pct:.0%} confidence", className="predicted-confidence-text"),
                ],
                className="predicted-winner-banner",
            ),

            # Probability bars
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                f"{away.team_name}",
                                style={"fontSize": "12px", "color": "#A5A5A5", "marginBottom": "4px", "textAlign": "right"}
                            ),
                            html.Div(
                                html.Div(className="prob-bar-fill-away", style={"width": f"{away_prob*100:.1f}%"}),
                                className="prob-bar-wrap",
                            ),
                            html.Div(f"{away_prob:.0%}", style={"fontSize": "14px", "fontWeight": "700", "color": "#42A5F5", "textAlign": "right"}),
                        ],
                        style={"textAlign": "right"},
                    ),
                    html.Div("vs", style={"textAlign": "center", "color": "#666", "fontSize": "12px"}),
                    html.Div(
                        [
                            html.Div(
                                f"{home.team_name}",
                                style={"fontSize": "12px", "color": "#A5A5A5", "marginBottom": "4px"}
                            ),
                            html.Div(
                                html.Div(className="prob-bar-fill-home", style={"width": f"{home_prob*100:.1f}%"}),
                                className="prob-bar-wrap",
                            ),
                            html.Div(f"{home_prob:.0%}", style={"fontSize": "14px", "fontWeight": "700", "color": "#CC0000"}),
                        ],
                    ),
                ],
                className="pre-game-prob-row",
            ),

            # Key factors
            html.Div("Key Factors", style={"fontSize": "11px", "fontWeight": "700", "letterSpacing": "1.5px", "color": "#777", "textTransform": "uppercase", "margin": "16px 0 8px"}),
            html.Div(
                [
                    html.Div(f"#{a_rank}" if a_rank else "NR", style={"textAlign": "right", "color": "#FFA500" if a_rank and a_rank <= 25 else "#A5A5A5", "fontWeight": "600"}),
                    html.Div("Ranking", className="factor-label"),
                    html.Div(f"#{h_rank}" if h_rank else "NR", style={"color": "#FFA500" if h_rank and h_rank <= 25 else "#A5A5A5", "fontWeight": "600"}),

                    html.Div(a_record, style={"textAlign": "right", "color": "#A5A5A5"}),
                    html.Div("Record", className="factor-label"),
                    html.Div(h_record, style={"color": "#A5A5A5"}),

                    html.Div("", style={}),
                    html.Div("Location", className="factor-label"),
                    html.Div(location_text, style={"color": "#A5A5A5", "fontSize": "12px"}),
                ],
                className="key-factors-grid",
            ),

            html.Div(
                "Live predictions begin at tip-off",
                className="pre-game-footer-note",
            ),
        ],
        className="pre-game-prediction-container",
    )


def build_prob_chart(game, history, win_prob=None) -> html.Div:
    """Build an enhanced line chart showing win probability over time for both teams."""
    status = getattr(game, "status", "in")
    if status == "pre":
        return build_pre_game_analysis(game, win_prob)

    if not history or len(history) < 1:
        return html.Div(
            [
                html.H6("Live Win Probability", className="chart-title mb-3"),
                html.P(
                    "Waiting for live game data...",
                    className="text-muted text-center p-5"
                )
            ],
            className="prob-chart-container"
        )

    # Support both old and new data formats during transition
    times_secs = [h.get("time_secs", i) for i, h in enumerate(history)]
    times_str = [h.get("time_str", h.get("time", "??")) for h in history]

    home_probs = [h.get("prob", 0.5) * 100 for h in history]
    away_probs = [(1.0 - h.get("prob", 0.5)) * 100 for h in history]

    home_name = game.home.team_name
    away_name = game.away.team_name

    # Get current probabilities (last data point)
    current_home_prob = home_probs[-1] if home_probs else 50
    current_away_prob = away_probs[-1] if away_probs else 50

    fig = go.Figure()

    # Home team line (solid, thick)
    fig.add_trace(go.Scatter(
        x=times_secs, y=home_probs,
        mode='lines+markers',
        name=home_name,
        line=dict(color='#CC0000', width=4),
        marker=dict(size=7, line=dict(color='#FFFFFF', width=1)),
        fill='tozeroy',
        fillcolor='rgba(204, 0, 0, 0.1)',
        hovertemplate=f"<b>{home_name}</b><br>Time: %{{customdata}}<br>Win Prob: %{{y:.1f}}%<extra></extra>",
        customdata=times_str,
        connectgaps=False
    ))

    # Away team line (dashed, thick)
    fig.add_trace(go.Scatter(
        x=times_secs, y=away_probs,
        mode='lines+markers',
        name=away_name,
        line=dict(color='#42A5F5', width=4, dash='dash'),
        marker=dict(size=7, line=dict(color='#FFFFFF', width=1)),
        fill='tonexty',        fillcolor='rgba(66, 165, 245, 0.1)',
        hovertemplate=f"<b>{away_name}</b><br>Time: %{{x}}<br>Win Prob: %{{y:.1f}}%<extra></extra>",
        connectgaps=False
    ))

    # Add 50% reference line
    fig.add_hline(
        y=50,
        line_dash="dot",
        line_color="#666666",
        line_width=1,
        annotation_text="50%",
        annotation_position="right",
        annotation_font_color="#666666"
    )

    fig.update_layout(
        title=dict(
            text="<b>Live Win Probability Trend (Elapsed Game Time)</b>",
            font=dict(size=16, color="#FFFFFF")
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(15,15,15,0.5)',
        margin=dict(l=60, r=100, t=50, b=80),
        height=450,
        xaxis=dict(
            type='linear',
            showgrid=True,
            gridcolor='rgba(51,51,51,0.3)',
            gridwidth=1,
            tickfont=dict(color='#A5A5A5', size=11),
            title=dict(
                text="<b>Elapsed Time (MM:SS from Game Start)</b>",
                font=dict(color='#FFFFFF', size=12)
            ),
            zeroline=False,
            tickangle=-45,
            tickmode='array',
            tickvals=[i * 60 * 5 for i in range(9)], # Ticks every 5 minutes (0, 5, 10, ..., 40)
            ticktext=[f"{i*5}:00" for i in range(9)]
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(51,51,51,0.3)',
            gridwidth=1,
            tickfont=dict(color='#A5A5A5', size=11),
            range=[0, 100],
            title=dict(text="<b>Win Probability (%)</b>", font=dict(color='#FFFFFF', size=12)),
            zeroline=False
        ),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.98,
            xanchor="left",
            x=0.02,
            font=dict(color="#FFFFFF", size=12),
            bgcolor="rgba(0,0,0,0.3)",
            bordercolor="#333333",
            borderwidth=1
        ),
        hovermode='x unified',
        font=dict(family="Lexend, sans-serif", color="#FFFFFF")
    )

    # Current probability cards
    home_card = html.Div(
        [
            html.Div(home_name, className="prob-card-team-name"),
            html.Div(
                f"{current_home_prob:.1f}%",
                className="prob-card-percentage",
                style={"color": "#CC0000"}
            )
        ],
        className="prob-card home-card"
    )

    away_card = html.Div(
        [
            html.Div(away_name, className="prob-card-team-name"),
            html.Div(
                f"{current_away_prob:.1f}%",
                className="prob-card-percentage",
                style={"color": "#42A5F5"}
            )
        ],
        className="prob-card away-card"
    )

    return html.Div(
        [
            html.Div(
                [
                    home_card,
                    away_card
                ],
                className="prob-cards-row"
            ),
            dcc.Graph(
                figure=fig,
                config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d'],
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': 'win_probability_chart',
                        'height': 450,
                        'width': 800,
                        'scale': 2
                    }
                },
                className="prob-graph",
                style={'height': '450px'}
            )
        ],
        className="prob-chart-container-enhanced"
    )


def build_game_panel_content(
    game: object | None,
    box_score: object | None,
    pbp: object | None,
    prob_history: list | None = None,
    win_prob: float | None = None,
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
            dbc.Tab(
                build_prob_chart(game, prob_history, win_prob=win_prob),
                label="Win Prob",
                tab_id="tab-prob",
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

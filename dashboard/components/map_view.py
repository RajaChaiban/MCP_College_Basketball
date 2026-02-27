"""
Build the US map Plotly figure showing today's college basketball games.
"""

from __future__ import annotations

from datetime import date

import plotly.graph_objects as go

from dashboard.data.geocoder import get_coords

# Status → marker color
STATUS_COLORS = {
    "in": "#CC0000",       # ESPN Red = live
    "post": "#444444",     # Gray = final
    "pre": "#FFFFFF",      # White = upcoming
}

STATUS_LABELS = {
    "in": "LIVE",
    "post": "Final",
    "pre": "Upcoming",
}


def build_map_figure(games: list, conference_filter: str = "") -> go.Figure:
    """
    Build a Scattergeo figure with one marker per game.

    Args:
        games: List of Game dicts (from games-store).
        conference_filter: If set, only show games matching this conference.

    Returns:
        go.Figure
    """
    lats, lons, texts, colors, sizes, custom_data, hover_texts = [], [], [], [], [], [], []
    games_to_plot = []

    for g_dict in games:
        # Extract fields from dict
        home_team = g_dict.get("home", {}).get("team_name", "Unknown")
        away_team = g_dict.get("away", {}).get("team_name", "Unknown")
        home_score = g_dict.get("home", {}).get("score", 0)
        away_score = g_dict.get("away", {}).get("score", 0)
        status = g_dict.get("status", "pre")
        status_detail = g_dict.get("status_detail", "")
        clock = g_dict.get("clock", "")
        game_id = g_dict.get("id", "")
        win_prob = g_dict.get("win_prob")
        
        # Get venue coordinates
        coords = get_coords(team_name=home_team)
        if not coords:
            coords = get_coords(team_name=away_team)
        if not coords:
            continue

        lat, lon = coords
        status_label = STATUS_LABELS.get(status, status)

        if status == "in":
            prob_text = ""
            if win_prob is not None:
                prob_text = f"<br>Win Prob: <b>{win_prob:.1%}</b> {home_team}"
            score_text = f"{away_team} {away_score} - {home_score} {home_team}"
            time_text = status_detail or clock or "In Progress"
            hover = f"<b>{score_text}</b><br>{time_text}{prob_text}<br><i>Click for details</i>"
        elif status == "post":
            score_text = f"{away_team} {away_score} - {home_score} {home_team}"
            hover = f"<b>{score_text}</b><br>Final<br><i>Click for box score</i>"
        else:
            if win_prob is not None:
                winner = home_team if win_prob >= 0.5 else away_team
                conf_pct = max(win_prob, 1 - win_prob)
                pred_text = f"<br>Prediction: <b>{winner}</b> favored ({conf_pct:.0%})"
            else:
                pred_text = ""
            hover = f"<b>{away_team} @ {home_team}</b><br>{status_detail or 'Upcoming'}{pred_text}"
            if g_dict.get("broadcast"):
                hover += f"<br>📺 {g_dict['broadcast']}"

        lats.append(lat)
        lons.append(lon)
        hover_texts.append(hover)
        colors.append(STATUS_COLORS.get(status, "#42A5F5"))
        sizes.append(18 if status == "in" else 12)
        custom_data.append(game_id)
        games_to_plot.append({"status": status, "win_prob": win_prob, "lat": lat, "lon": lon})

    fig = go.Figure()

    # Add game markers
    if lats:
        fig.add_trace(
            go.Scattergeo(
                lat=lats,
                lon=lons,
                text=hover_texts,
                hovertemplate="%{text}<extra></extra>",
                marker=dict(
                    color=colors,
                    size=sizes,
                    line=dict(color="#333333", width=1),
                    opacity=1.0,
                ),
                customdata=custom_data,
                mode="markers",
                name="Games",
                showlegend=False,
            )
        )

    # Add orange prediction ring for pre-game games with a prediction
    pre_lats = [g["lat"] for g in games_to_plot if g["status"] == "pre" and g["win_prob"] is not None]
    pre_lons = [g["lon"] for g in games_to_plot if g["status"] == "pre" and g["win_prob"] is not None]
    if pre_lats:
        fig.add_trace(go.Scattergeo(
            lat=pre_lats,
            lon=pre_lons,
            mode="markers",
            marker=dict(
                size=22,
                color="rgba(255, 165, 0, 0.15)",
                symbol="circle-open",
                line=dict(width=2, color="#FFA500"),
            ),
            hoverinfo="none",
            showlegend=False,
        ))

    # Add legend traces (invisible markers just for the legend)
    for status, color in STATUS_COLORS.items():
        fig.add_trace(
            go.Scattergeo(
                lat=[None],
                lon=[None],
                mode="markers",
                marker=dict(color=color, size=10),
                name=STATUS_LABELS[status],
                showlegend=True,
            )
        )

    fig.update_layout(
        geo=dict(
            scope="usa",
            projection_type="albers usa",
            showland=True,
            landcolor="#1A1A1A",
            showocean=True,
            oceancolor="#000000",
            showlakes=True,
            lakecolor="#000000",
            showrivers=False,
            showcountries=False,
            showcoastlines=True,
            coastlinecolor="#333333",
            showsubunits=True,
            subunitcolor="#222222",
            bgcolor="#000000",
        ),
        paper_bgcolor="#000000",
        plot_bgcolor="#000000",
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=0.01,
            xanchor="right",
            x=0.99,
            font=dict(color="#FFFFFF", size=12),
            bgcolor="rgba(0,0,0,0.8)",
            bordercolor="#333333",
            borderwidth=1,
        ),
        uirevision="map",  # preserve zoom/pan on refresh
    )

    return fig


def build_empty_map() -> go.Figure:
    """Return a styled empty map (no games loaded yet)."""
    return build_map_figure([])

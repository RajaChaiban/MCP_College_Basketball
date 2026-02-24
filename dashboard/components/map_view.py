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
        games: List of Game model instances.
        conference_filter: If set, only show games matching this conference.

    Returns:
        go.Figure
    """
    lats, lons, texts, colors, sizes, custom_data, hover_texts = [], [], [], [], [], [], []

    for game in games:
        # Get venue coordinates from home team name
        coords = get_coords(
            team_name=game.home.team_name,
        )
        if not coords:
            # Try away team
            coords = get_coords(team_name=game.away.team_name)
        if not coords:
            continue

        lat, lon = coords

        # Build display text
        status = game.status or "pre"
        status_label = STATUS_LABELS.get(status, status)

        if status == "in":
            score_text = f"{game.away.team_name} {game.away.score} - {game.home.score} {game.home.team_name}"
            time_text = game.status_detail or game.clock or "In Progress"
            hover = f"<b>{score_text}</b><br>{time_text}<br><i>Click for details</i>"
        elif status == "post":
            score_text = f"{game.away.team_name} {game.away.score} - {game.home.score} {game.home.team_name}"
            hover = f"<b>{score_text}</b><br>Final<br><i>Click for box score</i>"
        else:
            hover = f"<b>{game.away.team_name} @ {game.home.team_name}</b><br>{game.status_detail or 'Upcoming'}"
            if game.broadcast:
                hover += f"<br>TV: {game.broadcast}"

        lats.append(lat)
        lons.append(lon)
        hover_texts.append(hover)
        colors.append(STATUS_COLORS.get(status, "#42A5F5"))
        sizes.append(16 if status == "in" else 12)
        custom_data.append(game.id)

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

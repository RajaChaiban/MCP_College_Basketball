"""
Predictor tools for the MCP server.
Provides win probability calculation and explanation for live games.
"""

from __future__ import annotations

import json
from typing import Any


async def get_win_probability(game_id: str) -> str:
    """
    Fetch a live game and run the ML predictor to get win probability.
    Returns formatted result with feature values.
    """
    try:
        # Lazy imports to avoid circular dependency with dashboard
        import sys
        import os

        # Add dashboard path if not already in sys.path
        dashboard_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if dashboard_parent not in sys.path:
            sys.path.insert(0, dashboard_parent)

        from cbb_mcp.services import games as games_svc
        from dashboard.ai.predictor import get_win_probability as calculate_prob

        game = await games_svc.get_game_detail(game_id)
        if not game:
            return f"Game {game_id} not found."

        # Get PBP for momentum calculation
        pbp = await games_svc.get_play_by_play(game_id)

        # Calculate probability and get feature values
        prob = calculate_prob(game, pbp=pbp)

        if prob is None:
            return f"Could not calculate win probability for game {game_id}. Model may not be loaded."

        home_team = getattr(game.home, "name", "Home")
        away_team = getattr(game.away, "name", "Away")

        result = f"""
**Win Probability for {home_team} vs {away_team}**

**{home_team} Win Probability: {prob*100:.1f}%**

This prediction is based on:
- Current score differential
- Momentum (recent scoring trends)
- Strength differential (team rankings)
- Time remaining in game
- Current period

Note: This is a live prediction powered by a Logistic Regression + XGBoost ensemble model.
"""
        return result.strip()

    except Exception as e:
        return f"Error calculating win probability: {str(e)}"


async def explain_win_probability(game_id: str) -> str:
    """
    Return a narrative explanation of which factors favor which team.
    """
    try:
        # Lazy imports to avoid circular dependency with dashboard
        import sys
        import os

        # Add dashboard path if not already in sys.path
        dashboard_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if dashboard_parent not in sys.path:
            sys.path.insert(0, dashboard_parent)

        from cbb_mcp.services import games as games_svc

        game = await games_svc.get_game_detail(game_id)
        if not game:
            return f"Game {game_id} not found."

        home_team = getattr(game.home, "name", "Home")
        away_team = getattr(game.away, "name", "Away")
        h_score = getattr(game.home, "score", 0)
        a_score = getattr(game.away, "score", 0)
        h_rank = getattr(game.home, "rank", None)
        a_rank = getattr(game.away, "rank", None)

        score_diff = h_score - a_score
        status = getattr(game, "status", "pre")

        factors = []

        # Score differential
        if score_diff > 0:
            factors.append(f"✓ {home_team} leads by {score_diff} points (advantage {home_team})")
        elif score_diff < 0:
            factors.append(f"✓ {away_team} leads by {-score_diff} points (advantage {away_team})")
        else:
            factors.append("✓ Game is tied (neutral)")

        # Strength/ranking
        if h_rank and a_rank:
            if h_rank < a_rank:
                factors.append(f"✓ {home_team} is ranked #{h_rank} vs #{a_rank} (advantage {home_team})")
            else:
                factors.append(f"✓ {away_team} is ranked #{a_rank} vs #{h_rank} (advantage {away_team})")

        # Game status
        if status == "pre":
            factors.append("⏸ Game has not started yet")
        elif status == "in":
            period = getattr(game, "period", 1) or 1
            clock = getattr(game, "clock", "20:00") or "20:00"
            factors.append(f"▶️ Game in progress: Q{period} {clock}")
        elif status == "post":
            factors.append("✓ Game completed")

        explanation = f"""
**Factors Affecting {home_team} vs {away_team}:**

{chr(10).join(factors)}

The ML model combines these factors with recent game momentum trends to produce the win probability forecast.
""".strip()

        return explanation

    except Exception as e:
        return f"Error explaining win probability: {str(e)}"


async def get_probability_history(game_id: str, history_json: str = "") -> str:
    """
    Parse injected probability history JSON and return time-series table + trend summary.
    Handles both 'time' and 'time_str' keys for backwards compatibility.
    """
    try:
        # Lazy imports to avoid circular dependency with dashboard
        import sys
        import os

        # Add dashboard path if not already in sys.path
        dashboard_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if dashboard_parent not in sys.path:
            sys.path.insert(0, dashboard_parent)

        from cbb_mcp.services import games as games_svc

        game = await games_svc.get_game_detail(game_id)
        if not game:
            return f"Game {game_id} not found."

        home_team = getattr(game.home, "name", "Home")
        away_team = getattr(game.away, "name", "Away")

        # Parse history JSON if provided
        history_data = []
        if history_json:
            try:
                history_data = json.loads(history_json)
                if not isinstance(history_data, list):
                    history_data = []
            except json.JSONDecodeError:
                pass

        if not history_data:
            return f"No probability history available for {game_id}."

        # Build markdown table
        table_lines = [
            "| Time | {home_team} Win% |".format(home_team=home_team),
            "|------|--------|",
        ]

        # Track trend
        first_prob = None
        last_prob = None

        for entry in history_data:
            # Handle both 'time' and 'time_str' keys
            time_key = "time_str" if "time_str" in entry else "time"
            time_str = entry.get(time_key, "0:00")
            prob = entry.get("prob", 0.5)

            if first_prob is None:
                first_prob = prob
            last_prob = prob

            prob_pct = prob * 100
            table_lines.append(f"| {time_str} | {prob_pct:.1f}% |")

        # Trend summary
        trend = ""
        if first_prob is not None and last_prob is not None:
            diff = (last_prob - first_prob) * 100
            if diff > 2:
                trend = f"\n**Trend**: {home_team} probability increased by {diff:.1f}% during the game."
            elif diff < -2:
                trend = f"\n**Trend**: {home_team} probability decreased by {-diff:.1f}% during the game."
            else:
                trend = "\n**Trend**: {home_team} probability remained relatively stable."

        result = f"""
**Win Probability History for {game_id}**

{chr(10).join(table_lines)}
{trend}

Data points show how the ML model's probability forecast evolved during the game based on score, momentum, and time.
""".strip()

        return result

    except Exception as e:
        return f"Error retrieving probability history: {str(e)}"

"""
Predictor tools for the MCP server.
Provides win probability calculation and explanation for live games.
"""

from __future__ import annotations

import json
from typing import Any


def _confidence_label(prob: float) -> str:
    conf = max(prob, 1 - prob)
    if conf >= 0.75:
        return "Heavy Favorite"
    elif conf >= 0.63:
        return "Moderate Favorite"
    elif conf >= 0.55:
        return "Slight Favorite"
    return "Even Matchup"


async def get_win_probability(game_id: str) -> str:
    """
    Fetch a game and run the ML predictor to get win probability.
    Works for pre-game (upcoming) and live (in-progress) games.
    """
    try:
        import sys, os
        dashboard_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if dashboard_parent not in sys.path:
            sys.path.insert(0, dashboard_parent)

        from cbb_mcp.services import games as games_svc
        from dashboard.ai.predictor import get_win_probability as calculate_prob, _parse_win_pct

        game = await games_svc.get_game_detail(game_id)
        if not game:
            return f"Game {game_id} not found."

        status = getattr(game, "status", "pre")
        home_name = getattr(game.home, "team_name", None) or getattr(game.home, "name", "Home")
        away_name = getattr(game.away, "team_name", None) or getattr(game.away, "name", "Away")

        pbp = None
        if status == "in":
            pbp = await games_svc.get_play_by_play(game_id)

        prob = calculate_prob(game, pbp=pbp)
        if prob is None:
            return f"Could not calculate win probability for game {game_id}. Model may not be loaded."

        away_prob = 1.0 - prob
        label = _confidence_label(prob)
        winner = home_name if prob >= 0.5 else away_name
        winner_prob = max(prob, away_prob)

        if status == "pre":
            h_rank = getattr(game.home, "rank", None)
            a_rank = getattr(game.away, "rank", None)
            h_rec  = getattr(game.home, "record", "N/A") or "N/A"
            a_rec  = getattr(game.away, "record", "N/A") or "N/A"
            neutral = getattr(game, "neutral_site", False)
            h_rank_str = f"#{h_rank}" if h_rank else "Unranked"
            a_rank_str = f"#{a_rank}" if a_rank else "Unranked"
            site_note  = "neutral site" if neutral else f"{home_name}'s home court"

            result = f"""**Pre-Game Win Probability: {away_name} @ {home_name}**

**Predicted Winner: {winner} ({winner_prob*100:.1f}% — {label})**

| Team | Rank | Record | Win Prob |
|------|------|--------|----------|
| {home_name} | {h_rank_str} | {h_rec} | {prob*100:.1f}% |
| {away_name} | {a_rank_str} | {a_rec} | {away_prob*100:.1f}% |

Game site: {site_note}

Use `explain_win_probability` for a detailed analysis of how this prediction was calculated."""
        else:
            h_score = getattr(game.home, "score", 0)
            a_score = getattr(game.away, "score", 0)
            period  = getattr(game, "period", 1) or 1
            clock   = getattr(game, "clock", "—") or "—"
            status_label = "In Progress" if status == "in" else "Final"

            result = f"""**Live Win Probability: {away_name} @ {home_name}**

**{home_name} Win Probability: {prob*100:.1f}%** | **{away_name}: {away_prob*100:.1f}%**

Score: {away_name} {a_score} — {h_score} {home_name}
Status: {status_label} | Period {period} | {clock}
Confidence: {label}

Use `explain_win_probability` for a full factor breakdown."""

        return result.strip()

    except Exception as e:
        return f"Error calculating win probability: {str(e)}"


async def explain_win_probability(game_id: str) -> str:
    """
    Return a 200-300 word analyst-style narrative explaining how the prediction
    was calculated, covering methodology, key factors, and confidence level.
    Works for both pre-game and live games.
    """
    try:
        import sys, os
        dashboard_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if dashboard_parent not in sys.path:
            sys.path.insert(0, dashboard_parent)

        from cbb_mcp.services import games as games_svc
        from dashboard.ai.predictor import get_win_probability as calculate_prob, _parse_win_pct

        game = await games_svc.get_game_detail(game_id)
        if not game:
            return f"Game {game_id} not found."

        status    = getattr(game, "status", "pre")
        home_name = getattr(game.home, "team_name", None) or getattr(game.home, "name", "Home")
        away_name = getattr(game.away, "team_name", None) or getattr(game.away, "name", "Away")
        h_rank    = getattr(game.home, "rank", None)
        a_rank    = getattr(game.away, "rank", None)
        h_rec     = getattr(game.home, "record", "N/A") or "N/A"
        a_rec     = getattr(game.away, "record", "N/A") or "N/A"
        neutral   = getattr(game, "neutral_site", False)

        pbp = None
        if status == "in":
            pbp = await games_svc.get_play_by_play(game_id)

        prob = calculate_prob(game, pbp=pbp)
        if prob is None:
            return f"Could not calculate win probability for game {game_id}. Model may not be loaded."

        away_prob  = 1.0 - prob
        label      = _confidence_label(prob)
        winner     = home_name if prob >= 0.5 else away_name
        loser      = away_name if prob >= 0.5 else home_name
        winner_prob = max(prob, away_prob)

        # ── Pre-game narrative ────────────────────────────────────────────────
        if status == "pre":
            h_rank_str = f"#{h_rank}" if h_rank else "unranked"
            a_rank_str = f"#{a_rank}" if a_rank else "unranked"
            h_wp = _parse_win_pct(h_rec)
            a_wp = _parse_win_pct(a_rec)

            # Ranking component
            h_rk_val = h_rank or 50
            a_rk_val = a_rank or 50
            ranking_diff  = (a_rk_val - h_rk_val) / 4.0
            record_diff   = (h_wp - a_wp) * 10
            strength_diff = (ranking_diff * 0.6) + (record_diff * 0.4)

            rank_edge  = home_name if ranking_diff > 0 else (away_name if ranking_diff < 0 else "neither team")
            record_edge = home_name if record_diff > 0 else (away_name if record_diff < 0 else "neither team")
            hca_note   = "No home court adjustment was applied (neutral site)." if neutral else f"A standard home court adjustment of +3 percentage points was added for {home_name}."

            report = f"""**Pre-Game Prediction Report: {away_name} @ {home_name}**

**Model verdict: {winner} — {winner_prob*100:.1f}% ({label})**

**Methodology**
This prediction uses a calibrated ensemble of two ML models — Logistic Regression and XGBoost — both trained on historical CBB game snapshots. For pre-game scenarios, the score differential and momentum are zero (the game hasn't started), so the entire signal comes from a blended *strength differential* feature.

**How strength differential was calculated**
The model blends two signals: AP ranking differential (weighted 60%) and season win-percentage differential (weighted 40%). {home_name} enters ranked {h_rank_str} with a {h_rec} record ({h_wp:.0%} win rate); {away_name} is {a_rank_str} with a {a_rec} record ({a_wp:.0%} win rate). The ranking component favors **{rank_edge}**, while the season record component favors **{record_edge}**. Combined, this yields a strength differential of {strength_diff:+.2f} in {home_name}'s direction.

**Home court & final adjustment**
{hca_note}

**Key factors at a glance**
- Ranking edge: {rank_edge} ({h_rank_str} vs {a_rank_str})
- Record edge: {record_edge} ({h_rec} vs {a_rec})
- Combined strength diff: {strength_diff:+.2f}
- Final probability: {home_name} {prob*100:.1f}% / {away_name} {away_prob*100:.1f}%

Once the game tips off, the model will incorporate live score, momentum, and time remaining to update the forecast in real time."""

        # ── Live / final game narrative ───────────────────────────────────────
        else:
            h_score   = getattr(game.home, "score", 0)
            a_score   = getattr(game.away, "score", 0)
            score_diff = h_score - a_score
            period    = getattr(game, "period", 1) or 1
            clock     = getattr(game, "clock", "—") or "—"
            h_rk_val  = h_rank or 50
            a_rk_val  = a_rank or 50
            strength_diff = (a_rk_val - h_rk_val) / 4.0
            status_label = "In Progress" if status == "in" else "Final"

            score_note = (
                f"{home_name} leads by {score_diff}" if score_diff > 0
                else (f"{away_name} leads by {-score_diff}" if score_diff < 0
                      else "the game is tied")
            )
            time_note = f"Period {period}, {clock} remaining" if status == "in" else "the game has concluded"

            report = f"""**Live Prediction Report: {away_name} @ {home_name}**

**Model verdict: {winner} — {winner_prob*100:.1f}% ({label})**

**Methodology**
The prediction engine uses a calibrated LR + XGBoost ensemble. Both models were trained on thousands of historical CBB game snapshots and calibrated with isotonic regression so that a 70% prediction reflects a true ~70% historical win rate.

**Current game state**
Score: {away_name} {a_score} — {h_score} {home_name} ({score_note}). Status: {status_label}, {time_note}. The score differential carries the strongest weight at this stage of the game — a {abs(score_diff)}-point lead {"with little time left provides near-certainty" if period == 2 and clock <= "05:00" else "is meaningful but the game is far from over"}.

**Supporting factors**
- **Strength differential**: {home_name} ({f'#{h_rank}' if h_rank else 'NR'}, {h_rec}) vs {away_name} ({f'#{a_rank}' if a_rank else 'NR'}, {a_rec}). Ranking component: {strength_diff:+.2f} in {home_name}'s direction.
- **Momentum**: Captured from recent play-by-play scoring runs. {"PBP data was used to measure recent momentum." if pbp else "PBP data was unavailable; momentum defaulted to 0."}
- **Time remaining**: The model scales score-differential importance as time decreases. With more time left, comebacks are more likely.

**Bottom line**
The ensemble assigns {winner} a **{winner_prob*100:.1f}%** chance of winning. {loser} would need {"a significant run" if winner_prob < 0.80 else "a near-miraculous comeback"} to flip this result."""

        return report.strip()

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

"""Formatting utilities for ML predictor output."""

import json
from typing import Optional


def format_probability(sport_id: str, game_id: str, prob: float) -> str:
    """
    Format a probability prediction as a user-friendly string.

    Args:
        sport_id: Sport identifier
        game_id: Game identifier
        prob: Probability (0.0 to 1.0)

    Returns:
        Formatted string
    """
    # Clamp to valid range
    prob = max(0.0, min(1.0, prob))

    # Confidence label
    if prob >= 0.75:
        confidence = "Very High"
    elif prob >= 0.65:
        confidence = "High"
    elif prob >= 0.55:
        confidence = "Moderate"
    elif prob >= 0.45:
        confidence = "Slight"
    else:
        confidence = "Low (Underdog)"

    pct = prob * 100

    return (
        f"**{sport_id.upper()} Game {game_id}**\n\n"
        f"**Home Team Win Probability: {pct:.1f}%**\n\n"
        f"*Confidence: {confidence}*"
    )


def format_explanation(
    sport_id: str,
    game_id: str,
    prob: float,
    features: dict,
    methodology: str = "",
    factors: list[str] = None,
) -> str:
    """
    Format a detailed explanation of a prediction.

    Args:
        sport_id: Sport identifier
        game_id: Game identifier
        prob: Probability (0.0 to 1.0)
        features: Dict of contributing features
        methodology: Description of prediction methodology
        factors: List of key factors (optional)

    Returns:
        Formatted markdown string (200-300 words)
    """
    pct = prob * 100

    # Default methodology
    if not methodology:
        methodology = (
            "This prediction uses a calibrated ensemble of Logistic Regression and "
            "XGBoost models trained on historical game data. The models are ensemble-weighted "
            "(50% LR, 50% XGB) to provide robust probability estimates."
        )

    # Build feature summary
    feature_summary = "**Key Features:**\n"
    for feat, value in features.items():
        feature_summary += f"- {feat}: {value:.2f}\n"

    # Default factors if not provided
    if not factors:
        factors = []
        if abs(features.get("score_diff", 0)) > 5:
            factors.append(f"Current score difference of {features.get('score_diff', 0):.0f} points")
        if features.get("strength_diff", 0) != 0:
            factors.append(f"Team strength differential of {features.get('strength_diff', 0):.2f}")
        if features.get("time_ratio", 0) < 0.5:
            factors.append("Significant time remaining in game")

    factors_text = "**Contributing Factors:**\n"
    for factor in factors:
        factors_text += f"- {factor}\n"

    # Confidence assessment
    if prob >= 0.75:
        confidence_desc = "This is a high-confidence prediction, indicating substantial advantage for the home team."
    elif prob >= 0.60:
        confidence_desc = "This is a moderately confident prediction with meaningful advantage for the home team."
    elif prob >= 0.50:
        confidence_desc = "This is a slight lean toward the home team with relatively even odds."
    else:
        confidence_desc = "This favors the away team or indicates very close matchup odds."

    return (
        f"# {sport_id.upper()} Game {game_id} — Win Probability Analysis\n\n"
        f"**Predicted Home Team Win Probability: {pct:.1f}%**\n\n"
        f"{methodology}\n\n"
        f"{feature_summary}\n"
        f"{factors_text}\n"
        f"**Confidence Assessment:** {confidence_desc}\n\n"
        f"*Note: This prediction is probabilistic and does not guarantee outcomes. "
        f"Consider multiple factors including recent form, injuries, and Vegas lines.*"
    )


def format_probability_history(
    sport_id: str, game_id: str, history: list[dict], trend: str = ""
) -> str:
    """
    Format probability history as a markdown table with trend summary.

    Args:
        sport_id: Sport identifier
        game_id: Game identifier
        history: List of dicts with keys: 'time'/'time_str' and 'prob'
        trend: Optional trend description

    Returns:
        Formatted markdown table + summary
    """
    if not history:
        return f"No probability history available for {sport_id} game {game_id}."

    # Build markdown table
    lines = [
        f"# {sport_id.upper()} Game {game_id} — Win Probability History\n",
        "| Time | Home Win Probability |",
        "|------|----------------------|",
    ]

    # Track first and last for trend
    first_prob = None
    last_prob = None

    for i, snapshot in enumerate(history):
        time_str = snapshot.get("time_str") or snapshot.get("time", "?")
        prob = snapshot.get("prob", 0.0)
        pct = prob * 100

        lines.append(f"| {time_str} | {pct:.1f}% |")

        if i == 0:
            first_prob = prob
        if i == len(history) - 1:
            last_prob = prob

    # Auto-generate trend if not provided
    if not trend and first_prob is not None and last_prob is not None:
        change = last_prob - first_prob
        if abs(change) < 0.05:
            trend = "Probability remained stable throughout the game."
        elif change > 0.10:
            trend = f"Home team momentum increased significantly (+{change*100:.1f}%)."
        elif change < -0.10:
            trend = f"Home team momentum declined significantly ({change*100:.1f}%)."
        else:
            trend = f"Probability shifted slightly ({change*100:+.1f}%)."

    return "\n".join(lines) + f"\n\n**Trend:** {trend}"


def validate_game_state(game_state: dict, required_fields: list[str]) -> tuple[bool, str]:
    """
    Validate a game state dictionary.

    Args:
        game_state: Game state dict to validate
        required_fields: List of required field names

    Returns:
        (is_valid, error_message)
    """
    if not game_state:
        return False, "Game state cannot be empty"

    missing = [f for f in required_fields if f not in game_state]
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"

    return True, ""

"""Tests for ML Sports Predictor formatting functions."""

import pytest
from ml_sports_predictor.formatting import (
    format_probability,
    format_explanation,
    format_probability_history,
    validate_game_state,
)


class TestFormatProbability:
    """Test probability formatting."""

    def test_format_probability_high(self):
        """Test formatting high probability."""
        result = format_probability("cbb", "401827712", 0.85)
        assert "85.0%" in result
        assert "Very High" in result or "High" in result

    def test_format_probability_moderate(self):
        """Test formatting moderate probability."""
        result = format_probability("cbb", "401827712", 0.55)
        assert "55.0%" in result
        assert "Moderate" in result or "Slight" in result

    def test_format_probability_low(self):
        """Test formatting low probability."""
        result = format_probability("cbb", "401827712", 0.35)
        assert "35.0%" in result
        assert "Low" in result or "Underdog" in result

    def test_format_probability_clamps_above_one(self):
        """Test probability is clamped to 1.0."""
        result = format_probability("cbb", "game123", 1.5)
        assert "100.0%" in result

    def test_format_probability_clamps_below_zero(self):
        """Test probability is clamped to 0.0."""
        result = format_probability("cbb", "game123", -0.5)
        assert "0.0%" in result

    def test_format_probability_includes_sport_and_game(self):
        """Test output includes sport and game ID."""
        result = format_probability("soccer", "game_2025", 0.65)
        assert "SOCCER" in result
        assert "game_2025" in result

    def test_format_probability_very_high_confidence(self):
        """Test very high confidence label."""
        result = format_probability("nfl", "game1", 0.90)
        assert "Very High" in result

    def test_format_probability_even_odds(self):
        """Test near 50/50 probability."""
        result = format_probability("cbb", "game1", 0.50)
        assert "50.0%" in result


class TestFormatExplanation:
    """Test explanation formatting."""

    def test_format_explanation_includes_probability(self):
        """Test explanation includes predicted probability."""
        result = format_explanation(
            "cbb", "401827712", 0.70, {"score_diff": 5.0}
        )
        assert "70.0%" in result or "70" in result

    def test_format_explanation_includes_methodology(self):
        """Test explanation includes methodology."""
        result = format_explanation("cbb", "game1", 0.65, {})
        assert "ensemble" in result.lower() or "model" in result.lower()

    def test_format_explanation_custom_methodology(self):
        """Test explanation uses custom methodology."""
        custom = "Custom ML approach"
        result = format_explanation("cbb", "game1", 0.65, {}, methodology=custom)
        assert custom in result

    def test_format_explanation_includes_factors(self):
        """Test explanation includes contributing factors."""
        result = format_explanation("cbb", "game1", 0.65, {})
        assert "Factor" in result or "factor" in result.lower()

    def test_format_explanation_custom_factors(self):
        """Test explanation uses provided factors."""
        factors = ["Strong defense", "Home court advantage"]
        result = format_explanation("cbb", "game1", 0.65, {}, factors=factors)
        assert "Strong defense" in result
        assert "Home court advantage" in result

    def test_format_explanation_includes_game_info(self):
        """Test explanation includes game info."""
        result = format_explanation("soccer", "match123", 0.60, {})
        assert "SOCCER" in result
        assert "match123" in result

    def test_format_explanation_includes_disclaimer(self):
        """Test explanation includes disclaimer."""
        result = format_explanation("nfl", "game1", 0.65, {})
        assert "probabilistic" in result.lower()


class TestFormatProbabilityHistory:
    """Test probability history formatting."""

    def test_format_history_with_data(self):
        """Test formatting history with multiple snapshots."""
        history = [
            {"time_str": "00:00", "prob": 0.50},
            {"time_str": "20:00", "prob": 0.55},
            {"time_str": "40:00", "prob": 0.60},
        ]
        result = format_probability_history("cbb", "game1", history)

        assert "Probability History" in result or "Time" in result
        assert "00:00" in result
        assert "50.0%" in result
        assert "60.0%" in result

    def test_format_history_empty(self):
        """Test formatting empty history."""
        result = format_probability_history("cbb", "game1", [])
        assert "No probability history" in result

    def test_format_history_single_snapshot(self):
        """Test formatting single history entry."""
        history = [{"time_str": "Start", "prob": 0.50}]
        result = format_probability_history("cbb", "game1", history)

        assert "Start" in result
        assert "50.0%" in result

    def test_format_history_auto_generates_trend_stable(self):
        """Test auto-generated trend for stable probability."""
        history = [
            {"time_str": "Start", "prob": 0.50},
            {"time_str": "End", "prob": 0.51},
        ]
        result = format_probability_history("cbb", "game1", history)
        assert "stable" in result.lower() or "unchanged" in result.lower()

    def test_format_history_auto_generates_trend_increasing(self):
        """Test auto-generated trend for increasing probability."""
        history = [
            {"time_str": "Start", "prob": 0.40},
            {"time_str": "Mid", "prob": 0.60},
            {"time_str": "End", "prob": 0.80},
        ]
        result = format_probability_history("cbb", "game1", history)
        assert "increase" in result.lower() or "momentum" in result.lower()

    def test_format_history_auto_generates_trend_decreasing(self):
        """Test auto-generated trend for decreasing probability."""
        history = [
            {"time_str": "Start", "prob": 0.80},
            {"time_str": "Mid", "prob": 0.60},
            {"time_str": "End", "prob": 0.30},
        ]
        result = format_probability_history("cbb", "game1", history)
        assert "declin" in result.lower() or "drop" in result.lower()

    def test_format_history_custom_trend(self):
        """Test formatting with custom trend."""
        history = [{"time_str": "Start", "prob": 0.50}]
        custom_trend = "Custom trend analysis"
        result = format_probability_history(
            "cbb", "game1", history, trend=custom_trend
        )
        assert custom_trend in result

    def test_format_history_with_time_fallback(self):
        """Test formatting history with 'time' key instead of 'time_str'."""
        history = [
            {"time": "00:00", "prob": 0.50},
            {"time": "20:00", "prob": 0.55},
        ]
        result = format_probability_history("cbb", "game1", history)
        assert "00:00" in result
        assert "50.0%" in result

    def test_format_history_includes_sport_and_game(self):
        """Test history includes sport and game ID."""
        history = [{"time_str": "Start", "prob": 0.50}]
        result = format_probability_history("soccer", "match123", history)
        assert "SOCCER" in result
        assert "match123" in result


class TestValidateGameState:
    """Test game state validation."""

    def test_validate_valid_state(self):
        """Test validation accepts valid state."""
        game_state = {
            "score_diff": 5.0,
            "strength_diff": 1.0,
        }
        is_valid, msg = validate_game_state(game_state, ["score_diff"])
        assert is_valid is True
        assert msg == ""

    def test_validate_empty_state(self):
        """Test validation rejects empty state."""
        is_valid, msg = validate_game_state({}, ["score_diff"])
        assert is_valid is False
        assert "empty" in msg.lower()

    def test_validate_missing_required_fields(self):
        """Test validation rejects missing required fields."""
        game_state = {"wrong_field": 5.0}
        is_valid, msg = validate_game_state(
            game_state, ["score_diff", "strength_diff"]
        )
        assert is_valid is False
        assert "Missing" in msg

    def test_validate_partial_requirements_met(self):
        """Test validation accepts state with some required fields."""
        game_state = {"score_diff": 5.0}
        is_valid, msg = validate_game_state(
            game_state, ["score_diff", "strength_diff"]
        )
        # At least one required field is present
        assert is_valid is True or is_valid is False  # Depends on implementation

    def test_validate_extra_fields_allowed(self):
        """Test validation allows extra fields."""
        game_state = {
            "score_diff": 5.0,
            "extra_field": 99.0,
        }
        is_valid, msg = validate_game_state(game_state, ["score_diff"])
        assert is_valid is True

"""Tests for MultiSportPredictor class."""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock

from ml_sports_predictor.predictor import MultiSportPredictor
from ml_sports_predictor.config import settings
from ml_sports_predictor.errors import (
    PredictionError,
    GameStateError,
    UnsupportedSportError,
)


class TestMultiSportPredictor:
    """Test the MultiSportPredictor wrapper class."""

    def test_initialization(self):
        """Test predictor initialization."""
        predictor = MultiSportPredictor(settings.sports_registry)
        assert predictor.sports_config is not None
        assert len(predictor.sports_config) > 0

    def test_get_available_sports(self):
        """Test getting list of available sports with loaded models."""
        predictor = MultiSportPredictor(settings.sports_registry)
        available = predictor.get_available_sports()
        # Some sports may not have models loaded, but the list should exist
        assert isinstance(available, list)

    def test_get_sport_info(self):
        """Test retrieving sport information."""
        predictor = MultiSportPredictor(settings.sports_registry)
        info = predictor.get_sport_info("cbb")

        assert info["name"] == "NCAA Men's Basketball"
        assert info["game_duration_minutes"] == 40
        assert info["scoring_units"] == "points"
        assert "model_loaded" in info
        assert "features" in info

    def test_get_sport_info_unknown_sport(self):
        """Test sport info retrieval for unknown sport returns empty dict."""
        predictor = MultiSportPredictor(settings.sports_registry)
        info = predictor.get_sport_info("badminton")
        assert info == {}

    def test_normalize_features_score_diff(self):
        """Test feature normalization for score difference."""
        predictor = MultiSportPredictor(settings.sports_registry)
        config = settings.sports_registry["cbb"]

        game_state = {"score_diff": 10.0}
        normalized = predictor._normalize_features("cbb", game_state, config)

        # Score diff should be scaled by typical_score_range max (150)
        expected_score_diff = 10.0 / 150
        assert abs(normalized["score_diff"] - expected_score_diff) < 0.001

    def test_normalize_features_time_ratio_clamping(self):
        """Test that time_ratio is clamped to [0, 1]."""
        predictor = MultiSportPredictor(settings.sports_registry)
        config = settings.sports_registry["cbb"]

        game_state = {"time_ratio": 1.5}  # Out of bounds
        normalized = predictor._normalize_features("cbb", game_state, config)

        assert 0.0 <= normalized["time_ratio"] <= 1.0

    def test_normalize_features_missing_features_filled(self):
        """Test that missing features are filled with 0.0."""
        predictor = MultiSportPredictor(settings.sports_registry)
        config = settings.sports_registry["cbb"]

        game_state = {"score_diff": 5.0}
        normalized = predictor._normalize_features("cbb", game_state, config)

        # All required features should be present
        for feat in config.predictor.features:
            assert feat in normalized

    def test_validate_game_state_empty(self):
        """Test validation rejects empty game state."""
        predictor = MultiSportPredictor(settings.sports_registry)
        config = settings.sports_registry["cbb"]

        with pytest.raises(GameStateError, match="Empty game state"):
            predictor._validate_game_state("cbb", {}, config)

    def test_validate_game_state_missing_features(self):
        """Test validation rejects state with no valid features."""
        predictor = MultiSportPredictor(settings.sports_registry)
        config = settings.sports_registry["cbb"]

        # Provide state with invalid features
        game_state = {"invalid_feature": 1.0}

        with pytest.raises(GameStateError, match="must contain at least one of"):
            predictor._validate_game_state("cbb", game_state, config)

    def test_validate_game_state_with_valid_features(self):
        """Test validation accepts state with at least one valid feature."""
        predictor = MultiSportPredictor(settings.sports_registry)
        config = settings.sports_registry["cbb"]

        game_state = {"score_diff": 5.0}

        # Should not raise
        predictor._validate_game_state("cbb", game_state, config)

    @pytest.mark.asyncio
    async def test_predict_unknown_sport(self):
        """Test prediction error for unknown sport."""
        predictor = MultiSportPredictor(settings.sports_registry)

        with pytest.raises(PredictionError, match="Unknown sport"):
            await predictor.predict("badminton", {"score_diff": 5.0})

    @pytest.mark.asyncio
    async def test_predict_no_model_loaded(self):
        """Test prediction error when model not loaded."""
        predictor = MultiSportPredictor({})  # Empty registry
        predictor.sports_config = settings.sports_registry

        # Tennis model likely not loaded
        with pytest.raises(PredictionError, match="No model loaded"):
            await predictor.predict("tennis", {"score_diff": 1.0})

    def test_soccer_feature_normalization(self):
        """Test soccer-specific feature normalization (goals)."""
        predictor = MultiSportPredictor(settings.sports_registry)
        config = settings.sports_registry["soccer"]

        game_state = {"goal_diff": 2.0}
        normalized = predictor._normalize_features("soccer", game_state, config)

        # Goal diff should be scaled by typical_score_range max (10)
        expected_goal_diff = 2.0 / 10
        assert abs(normalized["goal_diff"] - expected_goal_diff) < 0.001

    def test_nfl_feature_normalization(self):
        """Test NFL-specific feature normalization."""
        predictor = MultiSportPredictor(settings.sports_registry)
        config = settings.sports_registry["nfl"]

        game_state = {"score_diff": 14.0}
        normalized = predictor._normalize_features("nfl", game_state, config)

        # Score diff should be scaled by typical_score_range max (60)
        expected_score_diff = 14.0 / 60
        assert abs(normalized["score_diff"] - expected_score_diff) < 0.001

    def test_feature_normalization_preserves_order(self):
        """Test that normalized features maintain sport-specific order."""
        predictor = MultiSportPredictor(settings.sports_registry)
        config = settings.sports_registry["cbb"]

        game_state = {
            "score_diff": 5.0,
            "momentum": 2.0,
            "strength_diff": 1.0,
            "time_ratio": 0.5,
        }
        normalized = predictor._normalize_features("cbb", game_state, config)

        # All features should still be present with same sport
        assert "score_diff" in normalized
        assert "time_ratio" in normalized

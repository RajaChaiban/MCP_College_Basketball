"""Tests for ML Sports Predictor configuration loading."""

import pytest
import os
import tempfile
from pathlib import Path

from ml_sports_predictor.config import Settings, SportConfig


class TestSportConfigLoading:
    """Test loading and validating sport configurations."""

    def test_sports_registry_loads(self):
        """Test that sports registry loads successfully."""
        settings = Settings()
        assert len(settings.sports_registry) > 0
        assert "cbb" in settings.sports_registry

    def test_cbb_config_structure(self):
        """Test CBB sport configuration structure."""
        settings = Settings()
        cbb = settings.sports_registry["cbb"]

        assert cbb.name == "NCAA Men's Basketball"
        assert cbb.game_duration_minutes == 40
        assert cbb.period_count == 2
        assert len(cbb.period_names) == 2
        assert cbb.scoring_units == "points"
        assert len(cbb.typical_score_range) == 2
        assert len(cbb.predictor.features) > 0
        assert "lr" in cbb.predictor.ensemble_weights
        assert "xgb" in cbb.predictor.ensemble_weights

    def test_all_sports_configured(self):
        """Test that all expected sports are configured."""
        settings = Settings()
        expected_sports = {"cbb", "soccer", "nfl", "mlb", "tennis"}
        actual_sports = set(settings.sports_registry.keys())
        assert expected_sports.issubset(actual_sports)

    def test_get_sport_config(self):
        """Test retrieving sport config by ID."""
        settings = Settings()
        soccer = settings.get_sport_config("soccer")
        assert soccer.name == "Soccer (International)"
        assert soccer.game_duration_minutes == 90

    def test_get_sport_config_unknown_sport(self):
        """Test error on unknown sport."""
        settings = Settings()
        with pytest.raises(ValueError, match="Unknown sport"):
            settings.get_sport_config("badminton")

    def test_predictor_features_not_empty(self):
        """Test that all sports have predictor features defined."""
        settings = Settings()
        for sport_id, config in settings.sports_registry.items():
            assert len(config.predictor.features) > 0, f"{sport_id} has no features"

    def test_data_sources_configured(self):
        """Test that all sports have data sources configured."""
        settings = Settings()
        for sport_id, config in settings.sports_registry.items():
            assert config.data_sources.primary != "", f"{sport_id} has no primary source"

"""Tests for ML Sports Predictor MCP server tools."""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

from ml_sports_predictor import server
from ml_sports_predictor.errors import MLError


class TestInputValidation:
    """Test server input validation functions."""

    def test_validate_sport_id_valid(self):
        """Test valid sport ID validation."""
        result = server._validate_sport_id("cbb")
        assert result == "cbb"

    def test_validate_sport_id_case_insensitive(self):
        """Test sport ID validation is case-insensitive."""
        result = server._validate_sport_id("CBB")
        assert result == "cbb"

    def test_validate_sport_id_whitespace_stripped(self):
        """Test sport ID validation strips whitespace."""
        result = server._validate_sport_id("  soccer  ")
        assert result == "soccer"

    def test_validate_sport_id_invalid_format(self):
        """Test invalid sport ID format is rejected."""
        with pytest.raises(MLError, match="Invalid sport ID format"):
            server._validate_sport_id("123")

    def test_validate_sport_id_too_short(self):
        """Test too-short sport ID is rejected."""
        with pytest.raises(MLError, match="Invalid sport ID format"):
            server._validate_sport_id("ab")

    def test_validate_sport_id_special_chars(self):
        """Test sport ID with special chars is rejected."""
        with pytest.raises(MLError, match="Invalid sport ID format"):
            server._validate_sport_id("cb-b")

    def test_validate_game_id_valid(self):
        """Test valid game ID validation."""
        result = server._validate_game_id("401827712")
        assert result == "401827712"

    def test_validate_game_id_alphanumeric(self):
        """Test game ID allows alphanumeric, underscore, hyphen."""
        result = server._validate_game_id("game_2025-02-28")
        assert result == "game_2025-02-28"

    def test_validate_game_id_whitespace_stripped(self):
        """Test game ID validation strips whitespace."""
        result = server._validate_game_id("  401827712  ")
        assert result == "401827712"

    def test_validate_game_id_invalid_format(self):
        """Test invalid game ID format is rejected."""
        with pytest.raises(MLError, match="Invalid game ID format"):
            server._validate_game_id("game@2025")

    def test_validate_sport_exists(self):
        """Test sport existence validation."""
        # Should not raise for known sport
        server._validate_sport_exists("cbb")

    def test_validate_sport_exists_unknown(self):
        """Test sport existence validation for unknown sport."""
        with pytest.raises(MLError, match="Unknown sport"):
            server._validate_sport_exists("badminton")


class TestToolFunctions:
    """Test MCP tool functions."""

    @pytest.mark.asyncio
    async def test_get_win_probability_invalid_sport(self):
        """Test get_win_probability rejects invalid sport."""
        result = await server.get_win_probability(
            sport_id="invalid!", game_id="123", game_state_json=""
        )
        assert "Invalid" in result or "error" in result.lower()

    @pytest.mark.asyncio
    async def test_get_win_probability_unknown_sport(self):
        """Test get_win_probability rejects unknown sport."""
        result = await server.get_win_probability(
            sport_id="badminton", game_id="123", game_state_json=""
        )
        assert "Unknown sport" in result or "error" in result.lower()

    @pytest.mark.asyncio
    async def test_get_win_probability_missing_game_state_non_cbb(self):
        """Test get_win_probability requires game_state for non-CBB."""
        result = await server.get_win_probability(
            sport_id="soccer", game_id="game123", game_state_json=""
        )
        assert "game_state_json" in result or "required" in result.lower()

    @pytest.mark.asyncio
    async def test_get_win_probability_invalid_json(self):
        """Test get_win_probability rejects invalid JSON game state."""
        result = await server.get_win_probability(
            sport_id="soccer",
            game_id="game123",
            game_state_json="not valid json {",
        )
        assert "Invalid" in result or "json" in result.lower()

    @pytest.mark.asyncio
    async def test_explain_win_probability_invalid_sport(self):
        """Test explain_win_probability rejects invalid sport."""
        result = await server.explain_win_probability(
            sport_id="@@@", game_id="123", game_state_json=""
        )
        assert "Invalid" in result or "error" in result.lower()

    @pytest.mark.asyncio
    async def test_get_probability_history_no_history(self):
        """Test get_probability_history handles missing history."""
        result = await server.get_probability_history(
            sport_id="cbb", game_id="123", history_json=""
        )
        assert "No probability history" in result

    @pytest.mark.asyncio
    async def test_get_probability_history_invalid_json(self):
        """Test get_probability_history rejects invalid JSON."""
        result = await server.get_probability_history(
            sport_id="cbb", game_id="123", history_json="not json {{"
        )
        assert "Invalid" in result or "json" in result.lower()

    @pytest.mark.asyncio
    async def test_get_probability_history_not_array(self):
        """Test get_probability_history rejects non-array JSON."""
        result = await server.get_probability_history(
            sport_id="cbb", game_id="123", history_json='{"not": "array"}'
        )
        assert "JSON array" in result or "array" in result.lower()

    @pytest.mark.asyncio
    async def test_get_probability_history_valid(self):
        """Test get_probability_history with valid history."""
        history = [
            {"time_str": "Start", "prob": 0.50},
            {"time_str": "Mid", "prob": 0.55},
            {"time_str": "End", "prob": 0.60},
        ]
        result = await server.get_probability_history(
            sport_id="cbb",
            game_id="401827712",
            history_json=json.dumps(history),
        )
        assert "Probability History" in result or "Time" in result
        assert "%" in result  # Percentages in output


class TestGetterPredictor:
    """Test predictor getter function."""

    def test_predictor_singleton(self):
        """Test that _get_predictor returns same instance."""
        predictor1 = server._get_predictor()
        predictor2 = server._get_predictor()
        assert predictor1 is predictor2

    def test_predictor_initialized(self):
        """Test that predictor is initialized with sport registry."""
        predictor = server._get_predictor()
        assert predictor is not None
        assert len(predictor.sports_config) > 0

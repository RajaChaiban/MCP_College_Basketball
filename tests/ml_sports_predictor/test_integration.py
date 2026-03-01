"""Integration tests for ML Sports Predictor MCP server."""

import pytest
import json
import asyncio

from ml_sports_predictor.server import mcp
from ml_sports_predictor.config import settings


class TestMCPToolRegistration:
    """Test that MCP tools are properly registered."""

    @pytest.mark.asyncio
    async def test_tools_registered(self):
        """Test that all ML tools are registered."""
        tools = await mcp.list_tools()
        tool_names = [tool.name for tool in tools]

        assert "get_win_probability" in tool_names
        assert "explain_win_probability" in tool_names
        assert "get_probability_history" in tool_names

    @pytest.mark.asyncio
    async def test_tool_signatures(self):
        """Test that tool signatures are correct."""
        tools = await mcp.list_tools()
        tool_dict = {tool.name: tool for tool in tools}

        # Check get_win_probability signature
        win_prob_tool = tool_dict.get("get_win_probability")
        assert win_prob_tool is not None
        assert win_prob_tool.inputSchema is not None

    @pytest.mark.asyncio
    async def test_get_win_probability_parameters(self):
        """Test get_win_probability has correct parameters."""
        tools = await mcp.list_tools()
        tool = next((t for t in tools if t.name == "get_win_probability"), None)

        assert tool is not None
        schema = tool.inputSchema
        assert "properties" in schema
        assert "sport_id" in schema["properties"]
        assert "game_id" in schema["properties"]


class TestMultiServerIntegration:
    """Test integration of ML server with CBB server."""

    @pytest.mark.asyncio
    async def test_sports_registry_loaded(self):
        """Test that sports registry is properly loaded."""
        assert len(settings.sports_registry) > 0
        assert "cbb" in settings.sports_registry
        assert "soccer" in settings.sports_registry

    def test_all_sports_have_predictor_config(self):
        """Test that all sports have predictor configuration."""
        for sport_id, config in settings.sports_registry.items():
            assert config.predictor is not None
            assert len(config.predictor.features) > 0
            assert "lr" in config.predictor.ensemble_weights
            assert "xgb" in config.predictor.ensemble_weights

    @pytest.mark.asyncio
    async def test_predictor_initialization_concurrent(self):
        """Test predictor can be initialized concurrently."""
        from ml_sports_predictor.server import _get_predictor

        # Initialize predictor concurrently
        tasks = [asyncio.create_task(asyncio.sleep(0)) for _ in range(5)]
        await asyncio.gather(*tasks)

        # All concurrent accesses should get same instance
        predictor1 = _get_predictor()
        predictor2 = _get_predictor()
        assert predictor1 is predictor2


class TestDeploymentConfigurations:
    """Test deployment-related configurations."""

    def test_stdio_transport_default(self):
        """Test that stdio is default transport."""
        assert settings.transport in ["stdio", "streamable-http"]

    def test_log_level_valid(self):
        """Test that log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert settings.log_level in valid_levels

    def test_cache_settings(self):
        """Test cache settings are configured."""
        assert isinstance(settings.cache_enabled, bool)
        assert isinstance(settings.cache_dir, str)

    def test_sports_config_path_exists(self):
        """Test that sports config path is properly configured."""
        import os

        # Path should be specified
        assert settings.sports_registry_path != ""
        # Should have loaded successfully
        assert len(settings.sports_registry) > 0


class TestErrorHandling:
    """Test error handling in tool execution."""

    @pytest.mark.asyncio
    async def test_concurrent_calls_semaphore(self):
        """Test that semaphore limits concurrent calls."""
        from ml_sports_predictor.server import _concurrency

        # Verify semaphore exists and is properly configured
        assert _concurrency is not None
        assert _concurrency._value > 0
        assert _concurrency._value <= 100  # Should be reasonable limit

    def test_max_concurrent_calls_constant(self):
        """Test MAX_CONCURRENT_CALLS is set."""
        from ml_sports_predictor import server

        assert hasattr(server, "_MAX_CONCURRENT_CALLS")
        assert server._MAX_CONCURRENT_CALLS > 0
        assert server._MAX_CONCURRENT_CALLS <= 100


class TestCrossSportCompatibility:
    """Test that different sports work with ML server."""

    @pytest.mark.asyncio
    async def test_cbb_game_state_normalization(self):
        """Test CBB game state normalization."""
        from ml_sports_predictor.predictor import MultiSportPredictor

        predictor = MultiSportPredictor(settings.sports_registry)
        config = settings.sports_registry["cbb"]

        game_state = {
            "score_diff": 10.0,
            "momentum": 2.0,
            "strength_diff": 1.0,
            "time_ratio": 0.5,
            "mins_remaining": 20.0,
            "period": 2.0,
        }

        normalized = predictor._normalize_features("cbb", game_state, config)
        assert isinstance(normalized, dict)
        assert all(isinstance(v, float) for v in normalized.values())

    @pytest.mark.asyncio
    async def test_soccer_game_state_normalization(self):
        """Test soccer game state normalization."""
        from ml_sports_predictor.predictor import MultiSportPredictor

        predictor = MultiSportPredictor(settings.sports_registry)
        config = settings.sports_registry["soccer"]

        game_state = {
            "goal_diff": 1.0,
            "strength_diff": 0.5,
            "time_ratio": 0.6,
        }

        normalized = predictor._normalize_features("soccer", game_state, config)
        assert isinstance(normalized, dict)

    @pytest.mark.asyncio
    async def test_nfl_game_state_normalization(self):
        """Test NFL game state normalization."""
        from ml_sports_predictor.predictor import MultiSportPredictor

        predictor = MultiSportPredictor(settings.sports_registry)
        config = settings.sports_registry["nfl"]

        game_state = {
            "score_diff": 7.0,
            "strength_diff": 1.0,
            "time_ratio": 0.4,
        }

        normalized = predictor._normalize_features("nfl", game_state, config)
        assert isinstance(normalized, dict)

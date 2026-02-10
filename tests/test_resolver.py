"""Tests for the source resolver."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from cbb_mcp.services.resolver import resolve, get_sources_for
from cbb_mcp.sources.base import DataCapability, DataSource
from cbb_mcp.utils.errors import AllSourcesFailedError, SourceError


class MockSource(DataSource):
    name = "mock"
    priority = 1

    def capabilities(self):
        return {DataCapability.LIVE_SCORES}

    async def get_live_scores(self, date, conference="", top25=False):
        return [{"id": "1", "score": "mock"}]


class FailingSource(DataSource):
    name = "failing"
    priority = 0

    def capabilities(self):
        return {DataCapability.LIVE_SCORES}

    async def get_live_scores(self, date, conference="", top25=False):
        raise SourceError("failing", "Always fails")


def test_get_sources_for():
    sources = get_sources_for(DataCapability.LIVE_SCORES)
    # All sources support live scores
    assert len(sources) >= 1


@pytest.mark.asyncio
async def test_resolve_fallback():
    """Test that resolver falls back to next source on failure."""
    failing = FailingSource()
    mock = MockSource()

    with patch("cbb_mcp.services.resolver._sources", [failing, mock]):
        result = await resolve(
            DataCapability.LIVE_SCORES,
            "get_live_scores",
            date="2025-02-09",
        )
    assert result == [{"id": "1", "score": "mock"}]


@pytest.mark.asyncio
async def test_resolve_all_fail():
    """Test that AllSourcesFailedError raised when all sources fail."""
    failing1 = FailingSource()
    failing1.name = "fail1"
    failing2 = FailingSource()
    failing2.name = "fail2"

    with patch("cbb_mcp.services.resolver._sources", [failing1, failing2]):
        with pytest.raises(AllSourcesFailedError):
            await resolve(
                DataCapability.LIVE_SCORES,
                "get_live_scores",
                date="2025-02-09",
            )

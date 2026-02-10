"""Shared test fixtures."""

import pytest


@pytest.fixture(autouse=True)
def disable_cache(monkeypatch):
    """Disable caching for all tests."""
    monkeypatch.setenv("CBB_CACHE_ENABLED", "false")

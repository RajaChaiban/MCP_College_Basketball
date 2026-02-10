"""Tests for the cache module."""

import time

import pytest

from cbb_mcp.utils import cache


@pytest.fixture(autouse=True)
def enable_cache(monkeypatch):
    """Re-enable caching for cache tests (overrides conftest disable)."""
    monkeypatch.setenv("CBB_CACHE_ENABLED", "true")
    # Reload settings
    from cbb_mcp.config import Settings
    s = Settings()
    monkeypatch.setattr("cbb_mcp.utils.cache.settings", s)
    cache._mem_cache.clear()
    yield
    cache._mem_cache.clear()


def test_put_and_get():
    cache.put("test", "key1", data={"score": 42}, ttl=60)
    result = cache.get("test", "key1")
    assert result == {"score": 42}


def test_miss_returns_none():
    result = cache.get("test", "nonexistent")
    assert result is None


def test_expiry():
    cache.put("test", "expire", data="old", ttl=0)
    # TTL of 0 means it should be expired immediately
    time.sleep(0.01)
    result = cache.get("test", "expire")
    assert result is None


def test_different_keys():
    cache.put("test", "a", data="alpha", ttl=60)
    cache.put("test", "b", data="beta", ttl=60)
    assert cache.get("test", "a") == "alpha"
    assert cache.get("test", "b") == "beta"


def test_clear():
    cache.put("test", "clear_me", data="data", ttl=60)
    cache.clear()
    assert cache.get("test", "clear_me") is None

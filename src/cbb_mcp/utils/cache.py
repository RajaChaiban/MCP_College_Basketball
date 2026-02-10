"""Two-layer TTL cache: in-memory + optional disk."""

import hashlib
import json
import time
from pathlib import Path

import structlog

from cbb_mcp.config import settings

logger = structlog.get_logger()

# In-memory cache: key -> (expire_time, data)
_mem_cache: dict[str, tuple[float, object]] = {}


def _cache_key(namespace: str, *args: str) -> str:
    raw = f"{namespace}:{'|'.join(args)}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _disk_path(key: str) -> Path:
    cache_dir = Path(settings.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{key}.json"


def get(namespace: str, *args: str) -> object | None:
    """Retrieve from cache (memory first, then disk). Returns None on miss."""
    if not settings.cache_enabled:
        return None

    key = _cache_key(namespace, *args)

    # Memory check
    entry = _mem_cache.get(key)
    if entry:
        expire, data = entry
        if time.time() < expire:
            return data
        else:
            del _mem_cache[key]

    # Disk check
    path = _disk_path(key)
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if time.time() < raw.get("expire", 0):
                data = raw["data"]
                _mem_cache[key] = (raw["expire"], data)
                return data
            else:
                path.unlink(missing_ok=True)
        except (json.JSONDecodeError, KeyError, OSError):
            path.unlink(missing_ok=True)

    return None


def put(namespace: str, *args: str, data: object, ttl: int) -> None:
    """Store in both memory and disk cache."""
    if not settings.cache_enabled:
        return

    key = _cache_key(namespace, *args)
    expire = time.time() + ttl

    _mem_cache[key] = (expire, data)

    try:
        path = _disk_path(key)
        path.write_text(
            json.dumps({"expire": expire, "data": data}, default=str),
            encoding="utf-8",
        )
    except OSError as e:
        logger.warning("cache_disk_write_failed", error=str(e))


def clear() -> None:
    """Clear all caches."""
    _mem_cache.clear()
    cache_dir = Path(settings.cache_dir)
    if cache_dir.exists():
        for f in cache_dir.glob("*.json"):
            f.unlink(missing_ok=True)

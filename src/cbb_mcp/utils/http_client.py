"""Shared async HTTP client with retry logic and response size limits."""

import asyncio

import aiohttp
import structlog

logger = structlog.get_logger()

_session: aiohttp.ClientSession | None = None

# Maximum response body size: 5 MB
MAX_RESPONSE_SIZE = 5 * 1024 * 1024


async def get_session() -> aiohttp.ClientSession:
    """Get or create a shared aiohttp session."""
    global _session
    if _session is None or _session.closed:
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        _session = aiohttp.ClientSession(
            timeout=timeout,
            headers={"User-Agent": "cbb-mcp/0.1.0"},
            read_bufsize=MAX_RESPONSE_SIZE,
        )
    return _session


async def close_session() -> None:
    """Close the shared session."""
    global _session
    if _session and not _session.closed:
        await _session.close()
        _session = None


async def fetch_json(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    retries: int = 2,
    backoff: float = 0.5,
) -> dict | list:
    """Fetch JSON from a URL with retry logic.

    Raises aiohttp.ClientError on failure after all retries.
    """
    session = await get_session()
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status == 429:
                    wait = backoff * (2 ** attempt)
                    logger.warning("rate_limited", url=url, wait=wait)
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()

                # Enforce response size limit
                body = await resp.read()
                if len(body) > MAX_RESPONSE_SIZE:
                    raise aiohttp.ClientPayloadError(
                        f"Response too large: {len(body)} bytes"
                    )

                import json as _json
                return _json.loads(body)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            last_error = e
            if attempt < retries:
                wait = backoff * (2 ** attempt)
                logger.warning(
                    "http_retry",
                    url=url,
                    attempt=attempt + 1,
                    error_type=type(e).__name__,
                )
                await asyncio.sleep(wait)

    raise last_error  # type: ignore[misc]

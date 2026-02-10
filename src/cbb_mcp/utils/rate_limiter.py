"""Token bucket rate limiter per source."""

import asyncio
import time


class TokenBucket:
    """Simple token bucket rate limiter."""

    def __init__(self, rate: float, capacity: int | None = None):
        self.rate = rate  # tokens per second
        self.capacity = capacity or int(rate * 2)
        self.tokens = float(self.capacity)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a token is available."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_refill = now

            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1


# Per-source limiters, lazily initialized
_limiters: dict[str, TokenBucket] = {}


def get_limiter(source: str, rate: float) -> TokenBucket:
    """Get or create a rate limiter for a source."""
    if source not in _limiters:
        _limiters[source] = TokenBucket(rate)
    return _limiters[source]

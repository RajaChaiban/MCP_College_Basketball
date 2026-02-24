"""
Shared async utilities for the dashboard.
Provides a background event loop so sync Dash callbacks can call async services.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any, Coroutine, TypeVar

T = TypeVar("T")

# Single background event loop shared by all async service calls
_loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
_loop_thread: threading.Thread = threading.Thread(
    target=_loop.run_forever, daemon=True, name="cbb-async"
)
_loop_thread.start()


def run_async(coro: Coroutine[Any, Any, T], timeout: float = 30.0) -> T:
    """
    Run an async coroutine from a synchronous Dash callback.
    Submits to the shared background event loop and blocks until done.
    """
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result(timeout=timeout)

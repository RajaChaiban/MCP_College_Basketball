"""
Persistent MCP stdio client for the dashboard.
Spawns the cbb-mcp server as a subprocess and keeps the connection alive
for the lifetime of the dashboard process.
"""

from __future__ import annotations

import asyncio
import os
import sys
from contextlib import AsyncExitStack

import structlog

logger = structlog.get_logger()

# Root of the project (one level above dashboard/)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SRC = os.path.join(_PROJECT_ROOT, "src")


class MCPClient:
    """Lazy-connecting MCP stdio client. Thread-safe via asyncio.Lock."""

    def __init__(self) -> None:
        self._session = None
        self._exit_stack: AsyncExitStack | None = None
        self._lock = asyncio.Lock()
        self._connected = False

    async def _connect(self) -> None:
        """Start the MCP server subprocess and initialize the session."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        env = {**os.environ, "PYTHONPATH": _SRC}

        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "cbb_mcp.server"],
            env=env,
        )

        self._exit_stack = AsyncExitStack()
        try:
            read, write = await self._exit_stack.enter_async_context(
                stdio_client(params)
            )
            self._session = await self._exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await self._session.initialize()
            self._connected = True
            logger.info("mcp_client_connected", transport="stdio")
        except Exception as e:
            logger.error("mcp_client_connect_failed", error=str(e))
            await self._exit_stack.aclose()
            self._exit_stack = None
            self._session = None
            raise

    async def ensure_connected(self) -> None:
        """Connect if not already connected (idempotent, thread-safe)."""
        if self._connected:
            return
        async with self._lock:
            if self._connected:
                return
            await self._connect()

    async def call_tool(self, tool_name: str, tool_args: dict) -> str:
        """
        Call an MCP tool and return the text result.
        Auto-reconnects if the session was lost.
        """
        try:
            await self.ensure_connected()
            result = await self._session.call_tool(tool_name, tool_args)
        except Exception as e:
            # Try to reconnect once
            logger.warning("mcp_tool_call_failed_retrying", tool=tool_name, error=str(e))
            self._connected = False
            self._session = None
            if self._exit_stack:
                try:
                    await self._exit_stack.aclose()
                except Exception:
                    pass
            self._exit_stack = None
            try:
                await self._connect()
                result = await self._session.call_tool(tool_name, tool_args)
            except Exception as e2:
                return f"Error calling {tool_name}: {e2}"

        # Extract text from result content blocks
        if not result or not result.content:
            return "(no result)"
        parts = []
        for block in result.content:
            if hasattr(block, "text") and block.text:
                parts.append(block.text)
        return "\n".join(parts) if parts else "(empty result)"

    async def list_tools(self) -> list[dict]:
        """List available tools from the MCP server."""
        await self.ensure_connected()
        result = await self._session.list_tools()
        return [
            {"name": t.name, "description": t.description or ""}
            for t in (result.tools or [])
        ]

    async def close(self) -> None:
        """Shut down the MCP connection."""
        if self._exit_stack:
            await self._exit_stack.aclose()
        self._connected = False
        self._session = None


# Module-level singleton — shared by all AI chat calls
_client: MCPClient | None = None


def get_client() -> MCPClient:
    """Return the shared MCPClient singleton."""
    global _client
    if _client is None:
        _client = MCPClient()
    return _client

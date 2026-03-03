"""Async client for ML Sports Predictor MCP server.

Communicates with the standalone ml_sports_predictor MCP server via stdio or HTTP.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

logger = logging.getLogger(__name__)


class MLMCPClient:
    """Async client for ML Sports Predictor MCP server."""

    def __init__(self, transport: str = "stdio"):
        """
        Initialize the ML MCP client.

        Args:
            transport: "stdio" (default) or "streamable-http"
        """
        self.session = None
        self.transport = transport
        self._context = None

    async def connect(self) -> None:
        """Establish connection to ML MCP server."""
        if self.session is not None:
            return  # Already connected

        try:
            if self.transport == "stdio":
                # Connect via stdio to local ML server subprocess
                server_params = StdioServerParameters(
                    command="python",
                    args=["-m", "ml_sports_predictor.server"],
                )

                # Use context manager for stdio_client
                self._context = stdio_client(server_params, errlog=sys.stderr)
                read, write = await self._context.__aenter__()

                # Create session with the stdio client — must unpack (read, write)
                self.session = ClientSession(read, write)
                await self.session.initialize()

                logger.info("ml_mcp_client_connected", transport="stdio")

            elif self.transport == "streamable-http":
                # HTTP mode (for cloud deployment)
                # This would require implementing StreamableHTTPClient
                # For now, we'll fall back to in-process
                logger.warning("streamable-http not yet implemented; ML server unavailable")
                raise ValueError("HTTP transport not yet implemented")
            else:
                raise ValueError(f"Unknown transport: {self.transport}")

        except Exception as e:
            logger.error("ml_mcp_client_connection_failed", error=str(e), transport=self.transport)
            raise

    async def call_tool(self, tool_name: str, tool_args: dict[str, Any]) -> str:
        """
        Call a tool on the ML MCP server.

        Args:
            tool_name: Name of the tool (e.g., "get_win_probability")
            tool_args: Arguments dict

        Returns:
            Tool result as string
        """
        try:
            await self.connect()

            if not self.session:
                return "ML MCP server connection failed."

            # Call tool via MCP session
            result = await self.session.call_tool(tool_name, tool_args)

            if result.isError:
                logger.warning(
                    "ml_tool_error", tool=tool_name, error=result.content
                )
                return f"Tool error: {result.content}"

            # Extract text content from result
            if result.content:
                # Result.content is a list of TextContent/... objects
                text_parts = []
                for item in result.content:
                    if hasattr(item, "text"):
                        text_parts.append(item.text)
                    elif isinstance(item, str):
                        text_parts.append(item)
                return "\n".join(text_parts) if text_parts else "No result"

            return "No result from tool"

        except Exception as e:
            logger.exception("ml_tool_call_failed", tool=tool_name, error=str(e))
            return f"Tool call failed: {e}"

    async def close(self) -> None:
        """Close the connection to ML MCP server."""
        if self.session:
            await self.session.close()
            self.session = None
        if self._context:
            await self._context.__aexit__(None, None, None)
            self._context = None


# Global client instance
_ml_client: MLMCPClient | None = None


def get_ml_client() -> MLMCPClient:
    """Get the singleton ML MCP client instance."""
    global _ml_client
    if _ml_client is None:
        _ml_client = MLMCPClient(transport="stdio")
    return _ml_client


async def close_ml_client() -> None:
    """Close the global ML MCP client."""
    global _ml_client
    if _ml_client:
        await _ml_client.close()
        _ml_client = None

"""
In-process predictor client for the dashboard.
Provides the same interface as MCPClient but calls predictor functions directly.
"""

from __future__ import annotations

from typing import Any


class PredictorClient:
    """In-process adapter for predictor tools. Mimics MCPClient interface."""

    async def call_tool(self, name: str, args: dict[str, Any]) -> str:
        """
        Call a predictor tool and return the text result.
        Lazy-imports to avoid circular imports.
        """
        try:
            from cbb_mcp import predictor_server

            if name == "get_win_probability":
                game_id = args.get("game_id", "")
                return await predictor_server.get_win_probability(game_id)

            elif name == "explain_win_probability":
                game_id = args.get("game_id", "")
                return await predictor_server.explain_win_probability(game_id)

            elif name == "get_probability_history":
                game_id = args.get("game_id", "")
                history_json = args.get("history_json", "")
                return await predictor_server.get_probability_history(game_id, history_json)

            else:
                return f"Unknown predictor tool: {name}"

        except Exception as e:
            return f"Error calling predictor tool {name}: {str(e)}"


# Module-level singleton
_predictor_client: PredictorClient | None = None


def get_predictor_client() -> PredictorClient:
    """Return the shared PredictorClient singleton."""
    global _predictor_client
    if _predictor_client is None:
        _predictor_client = PredictorClient()
    return _predictor_client

"""
Chat callbacks: user input → AI agent → display response.
"""

from __future__ import annotations

from dash import Input, Output, State, callback, no_update

from dashboard.components.chat_panel import render_chat_history
from dashboard.utils import run_async


def register_chat_callbacks(app) -> None:
    """Register chat panel callbacks."""

    @app.callback(
        Output("chat-history", "children"),
        Output("conversation-store", "data"),
        Output("chat-input", "value"),
        Output("chat-loading-dummy", "children"),
        Input("chat-send-btn", "n_clicks"),
        Input("chat-input", "n_submit"),
        State("chat-input", "value"),
        State("conversation-store", "data"),
        State("selected-game-store", "data"),
        prevent_initial_call=True,
    )
    def handle_chat(n_clicks, n_submit, user_input, history, selected_game):
        """Handle chat submission and run AI agent."""
        if not user_input or not user_input.strip():
            return no_update, no_update, no_update, no_update

        history = history or []

        # Build context from selected game
        context = {}
        if selected_game and selected_game.get("game_id"):
            context["selected_game_id"] = selected_game["game_id"]

        try:
            from dashboard.ai.agent import run_chat_turn

            response_text, updated_history = run_async(
                run_chat_turn(user_input.strip(), history, context),
                timeout=120.0,
            )
        except Exception as e:
            response_text = f"Error: {e}"
            updated_history = history + [
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": response_text},
            ]

        rendered = render_chat_history(updated_history)
        return rendered, updated_history, "", None

    @app.callback(
        Output("chat-panel", "is_open", allow_duplicate=True),
        Output("conversation-store", "data", allow_duplicate=True),
        Output("chat-history", "children", allow_duplicate=True),
        Input("close-chat-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def close_chat(n_clicks):
        if n_clicks:
            # Clear history elements and store data on close
            initial_msg = render_chat_history([]) 
            return False, [], initial_msg
        return no_update, no_update, no_update

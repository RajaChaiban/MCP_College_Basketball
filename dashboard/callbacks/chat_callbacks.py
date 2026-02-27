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
        State("prob-history-store", "data"),
        prevent_initial_call=True,
    )
    def handle_chat(n_clicks, n_submit, user_input, history, selected_game, prob_history):
        """Handle chat submission and run AI agent."""
        if not user_input or not user_input.strip():
            return no_update, no_update, no_update, no_update

        history = history or []

        # Build context from selected game
        context = {}
        try:
            if selected_game and isinstance(selected_game, dict) and selected_game.get("game_id"):
                game_id = selected_game["game_id"]
                context["selected_game_id"] = game_id

                # Include probability history for the selected game if available
                if prob_history and isinstance(prob_history, dict):
                    # Try with both string and original game_id as keys
                    game_history = prob_history.get(game_id) or prob_history.get(str(game_id)) or []
                    if game_history:
                        import json
                        context["prob_history_json"] = json.dumps(game_history)
        except Exception as e:
            # Log error but don't crash - history wasn't critical for basic chat
            import traceback
            print(f"[chat_callbacks] Error building context: {e}")
            traceback.print_exc()

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

"""
Chat callbacks: user input → AI agent → display response.
"""

from __future__ import annotations

from dash import Input, Output, State, callback, no_update

from dashboard.components.chat_panel import render_chat_history
from dashboard.utils import run_async


import random

def register_chat_callbacks(app) -> None:
    """Register chat panel callbacks."""

    # Client-side callback to handle Enter key and auto-resize in the textarea
    app.clientside_callback(
        """
        function(n_submit, value) {
            const input = document.getElementById('chat-input');
            if (!input) return 0;

            if (!input.hasKeyDownListener) {
                const resize = () => {
                    // Reset height to 'auto' to get the correct scrollHeight
                    input.style.height = 'auto';

                    // Get the scrollHeight and apply it
                    let newHeight = input.scrollHeight;

                    // Cap at max-height
                    const maxHeight = 200;
                    if (newHeight > maxHeight) {
                        newHeight = maxHeight;
                    }

                    // Ensure minimum height
                    if (newHeight < 42) {
                        newHeight = 42;
                    }

                    input.style.height = newHeight + 'px';
                };

                // Bind resize function to this input specifically
                input.addEventListener('input', function() {
                    resize();
                });

                // Also handle when user types (including Enter with Shift)
                input.addEventListener('keydown', function(e) {
                    // Handle Shift+Enter for multiline (just let it happen naturally)
                    if (e.key === 'Enter' && e.shiftKey) {
                        // Schedule resize for next frame after newline is added
                        setTimeout(resize, 0);
                    }
                    // Handle regular Enter to send
                    else if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        const btn = document.getElementById('chat-send-btn');
                        if (btn) {
                            btn.click();
                        }
                    }
                });

                // Resize on paste
                input.addEventListener('paste', () => {
                    setTimeout(resize, 10);
                });

                // Handle when input is cleared or changed externally
                input.addEventListener('change', resize);

                // Trigger resize on window resize
                window.addEventListener('resize', resize);

                input.hasKeyDownListener = true;

                // Initial resize
                setTimeout(resize, 100);

                // Also watch for Dash updating the value
                const originalSetAttribute = input.setAttribute;
                input.setAttribute = function(name, value) {
                    originalSetAttribute.call(this, name, value);
                    if (name === 'value') {
                        setTimeout(resize, 0);
                    }
                };
            }
            return 0;
        }
        """,
        Output("chat-input-trigger", "data"),
        Input("chat-input", "id"),
    )

    @app.callback(
        Output("chat-history", "children"),
        Output("conversation-store", "data"),
        Output("chat-input", "value"),
        Output("chat-loading-dummy", "children"),
        Input("chat-send-btn", "n_clicks"),
        State("chat-input", "value"),
        State("conversation-store", "data"),
        State("selected-game-store", "data"),
        State("prob-history-store", "data"),
        prevent_initial_call=True,
    )
    def handle_chat(n_clicks, user_input, history, selected_game, prob_history):
        """Handle chat submission and run AI agent."""
        if not user_input or not user_input.strip():
            return no_update, no_update, no_update, no_update

        history = history or []

        # Add user message to history immediately for state preservation
        # (Though Dash updates the whole list anyway)
        
        # Build context from selected game
        context = {}
        try:
            if selected_game and isinstance(selected_game, dict) and selected_game.get("game_id"):
                game_id = selected_game["game_id"]
                context["selected_game_id"] = game_id

                # Include probability history for the selected game if available
                if prob_history and isinstance(prob_history, dict):
                    game_history = prob_history.get(game_id) or prob_history.get(str(game_id)) or []
                    if game_history:
                        import json
                        context["prob_history_json"] = json.dumps(game_history)
        except Exception as e:
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
                {"role": "user", "parts": [{"text": user_input}]},
                {"role": "model", "parts": [{"text": response_text}]},
            ]

        # Use the updated render_chat_history from components.chat_panel
        # We don't show typing here because the callback has finished.
        rendered = render_chat_history(updated_history, show_typing=False)
        return rendered, updated_history, "", random.randint(0, 1000000)

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

"""
Chat callbacks: user input → AI agent → display response.
"""

from __future__ import annotations

from dash import Input, Output, State, callback, no_update, html
from flask import request

from dashboard.components.chat_panel import render_chat_history
from dashboard.utils import run_async
from dashboard.utils.rate_limiter import check_rate_limit, get_client_ip, get_remaining_questions


def register_chat_callbacks(app) -> None:
    """Register chat panel callbacks."""

    # Client-side callback: attach resize + Enter-key listeners once on mount
    app.clientside_callback(
        """
        function(_id) {
            function attachListeners() {
                const input = document.getElementById('chat-input');
                if (!input) {
                    setTimeout(attachListeners, 100);
                    return;
                }
                if (input._cbbListenersAttached) return;
                input._cbbListenersAttached = true;

                function resize() {
                    input.style.height = 'auto';
                    const maxH = 200, minH = 42;
                    const h = Math.max(minH, Math.min(input.scrollHeight, maxH));
                    input.style.height = h + 'px';
                    input.style.overflowY = h >= maxH ? 'auto' : 'hidden';
                }

                input.addEventListener('input', resize);
                input.addEventListener('paste', () => setTimeout(resize, 10));

                input.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter' && e.shiftKey) {
                        setTimeout(resize, 0);
                    } else if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        const btn = document.getElementById('chat-send-btn');
                        if (btn) btn.click();
                    }
                });

                // Watch for Dash clearing the value after send
                const observer = new MutationObserver(() => setTimeout(resize, 0));
                observer.observe(input, { attributes: true, attributeFilter: ['value'] });

                setTimeout(resize, 50);
            }
            attachListeners();
            return 0;
        }
        """,
        Output("chat-input-trigger", "data"),
        Input("chat-input", "id"),
    )

    # Client-side callback: reset textarea height when Dash clears it after send
    app.clientside_callback(
        """
        function(value) {
            const input = document.getElementById('chat-input');
            if (!input) return window.dash_clientside.no_update;
            if (!value) {
                input.style.height = '42px';
                input.style.overflowY = 'hidden';
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("chat-input-trigger", "data", allow_duplicate=True),
        Input("chat-input", "value"),
        prevent_initial_call=True,
    )

    # Client-side callback: scroll chat history to bottom after new messages arrive
    app.clientside_callback(
        """
        function(children) {
            setTimeout(function() {
                const hist = document.getElementById('chat-history');
                if (hist) {
                    hist.scrollTop = hist.scrollHeight;
                }
            }, 50);
            return window.dash_clientside.no_update;
        }
        """,
        Output("chat-input-trigger", "data", allow_duplicate=True),
        Input("chat-history", "children"),
        prevent_initial_call=True,
    )

    @app.callback(
        Output("chat-history", "children"),
        Output("conversation-store", "data"),
        Output("chat-input", "value"),
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
            return no_update, no_update, no_update

        history = history or []

        # --- Rate Limiting Check ---
        user_ip = get_client_ip(request)
        allowed, limit_message = check_rate_limit(user_ip)

        if not allowed:
            print(f"[Chat] Rate limit exceeded for IP {user_ip}: {limit_message}")
            remaining = get_remaining_questions(user_ip)

            # Show rate limit message to user
            error_response = f"{limit_message}\n\n(Remaining today: {remaining['daily_remaining']}/{remaining['daily_limit']})"
            updated_history = history + [
                {"role": "user", "parts": [{"text": user_input}]},
                {"role": "model", "parts": [{"text": error_response}]},
            ]
            rendered = render_chat_history(updated_history, show_typing=False)
            return rendered, updated_history, ""

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
            import sys

            print(f"[Chat] IP {user_ip}: Sending to agent: {user_input.strip()[:80]!r}", flush=True)
            sys.stdout.flush()
            response_text, updated_history = run_async(
                run_chat_turn(user_input.strip(), history, context),
                timeout=120.0,
            )
            print(f"[Chat] Got response: {response_text[:200]!r}", flush=True)
            sys.stdout.flush()
        except Exception as e:
            import traceback
            print(f"[Chat] ERROR: {type(e).__name__}: {e}", flush=True)
            traceback.print_exc()
            response_text = f"Error: {e}"
            updated_history = history + [
                {"role": "user", "parts": [{"text": user_input}]},
                {"role": "model", "parts": [{"text": response_text}]},
            ]

        # Use the updated render_chat_history from components.chat_panel
        # We don't show typing here because the callback has finished.
        print(f"[Chat] Rendering {len(updated_history)} messages", flush=True)
        rendered = render_chat_history(updated_history, show_typing=False)
        print(f"[Chat] Rendered HTML length: {len(str(rendered))}", flush=True)
        print(f"[Chat] Returning to UI", flush=True)
        return rendered, updated_history, ""

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

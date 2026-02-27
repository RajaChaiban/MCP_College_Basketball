"""
Chat panel UI component: chat history + input.
"""

from __future__ import annotations

from dash import html, dcc
import dash_bootstrap_components as dbc


def build_chat_panel() -> html.Div:
    """Build the chat panel layout (used inside offcanvas)."""
    return html.Div(
        [
            # Chat history display
            html.Div(
                id="chat-history",
                className="chat-history",
                children=[
                    html.Div(
                        className="chat-message-row assistant-row",
                        children=[
                            html.Div(
                                html.I(className="fas fa-robot"),
                                className="chat-avatar assistant-avatar",
                            ),
                            html.Div(
                                "Hi! Ask me anything about tonight's games, stats, or standings. "
                                "If you've clicked a game on the map, I have context about it.",
                                className="chat-message assistant-message",
                            ),
                        ],
                    )
                ],
            ),
            # Input area
            html.Div(
                [
                    dbc.Input(
                        id="chat-input",
                        placeholder="Ask about games, stats, rankings...",
                        type="text",
                        className="chat-input",
                        debounce=False,
                        n_submit=0,
                        autofocus=True,
                    ),
                    dbc.Button(
                        html.I(className="fas fa-paper-plane"),
                        id="chat-send-btn",
                        color="primary",
                        className="chat-send-btn",
                        n_clicks=0,
                    ),
                ],
                className="chat-input-row",
            ),
            # Loading indicator
            dcc.Loading(
                id="chat-loading",
                type="dot",
                color="#7B68EE",
                children=html.Div(id="chat-loading-dummy"),
                className="chat-loading",
            ),
        ],
        className="chat-panel",
    )


def render_chat_history(history: list[dict]) -> list:
    """
    Render the conversation history as HTML elements.
    Supports Gemini format: {"role": "user"|"model", "parts": [{"text": "..."}]}
    """
    elements = [
        html.Div(
            className="chat-message-row assistant-row",
            children=[
                html.Div(
                    html.I(className="fas fa-robot"),
                    className="chat-avatar assistant-avatar",
                ),
                html.Div(
                    "Hi! Ask me anything about tonight's games, stats, or standings.",
                    className="chat-message assistant-message",
                ),
            ],
        )
    ]

    for msg in history:
        role = msg.get("role", "user")

        # Extract text from Gemini-format parts
        parts = msg.get("parts", [])
        text_content = " ".join(
            p.get("text", "") for p in parts if isinstance(p, dict) and p.get("text")
        ).strip()

        # Fallback: old Anthropic format {"role": ..., "content": str}
        if not text_content:
            raw = msg.get("content", "")
            if isinstance(raw, str):
                text_content = raw

        if not text_content:
            continue

        is_user = role == "user"

        if is_user:
            elements.append(
                html.Div(
                    className="chat-message-row user-row",
                    children=[
                        html.Div(text_content, className="chat-message user-message"),
                        html.Div(
                            html.I(className="fas fa-user"),
                            className="chat-avatar user-avatar",
                        ),
                    ],
                )
            )
        else:
            elements.append(
                html.Div(
                    className="chat-message-row assistant-row",
                    children=[
                        html.Div(
                            html.I(className="fas fa-robot"),
                            className="chat-avatar assistant-avatar",
                        ),
                        html.Div(
                            dcc.Markdown(text_content, className="chat-markdown"),
                            className="chat-message assistant-message",
                        ),
                    ],
                )
            )

    return elements

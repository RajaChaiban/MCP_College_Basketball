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
                [
                    html.Div(
                        id="chat-history",
                        className="chat-history",
                        children=render_chat_history([]),
                    ),
                    # Loading indicator positioned at the bottom of the history
                    html.Div(
                        dcc.Loading(
                            id="chat-loading",
                            type="dot",
                            children=html.Div(id="chat-loading-dummy"),
                            overlay_style={"visibility":"visible", "opacity": "0.5", "backgroundColor": "transparent"},
                            color="var(--espn-red)",
                        ),
                        className="chat-loading-container",
                    ),
                ],
                style={"flex-grow": "1", "display": "flex", "flex-direction": "column", "position": "relative", "overflow": "hidden"}
            ),
            # Input area
            html.Div(
                [
                    dbc.Textarea(
                        id="chat-input",
                        placeholder="Ask about games, stats, rankings...",
                        className="chat-input",
                        rows=1,
                        debounce=False,
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
            # Trigger for client-side Enter key handling
            dcc.Store(id="chat-input-trigger", data=0),
        ],
        className="chat-panel",
    )


def render_typing_indicator() -> html.Div:
    """Render the 'assistant is thinking' dots."""
    return html.Div(
        className="chat-message-row assistant-row",
        children=[
            html.Div(
                html.I(className="fas fa-robot"),
                className="chat-avatar assistant-avatar",
            ),
            html.Div(
                className="typing-indicator",
                children=[
                    html.Div(className="typing-dot"),
                    html.Div(className="typing-dot"),
                    html.Div(className="typing-dot"),
                ],
            ),
        ],
        id="typing-indicator-row",
    )


def render_chat_history(history: list[dict], show_typing: bool = False) -> list:
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
                    "Hi! I'm your CBB Assistant. Ask me about tonight's games, rankings, or team stats!",
                    className="chat-message assistant-message",
                ),
            ],
        )
    ]

    for msg in history:
        role = msg.get("role", "user")
        
        # Extract text from Gemini-format parts or content string
        text_content = ""
        parts = msg.get("parts", [])
        if parts:
             text_content = " ".join(
                p.get("text", "") for p in parts if isinstance(p, dict) and p.get("text")
            ).strip()
        
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

    if show_typing:
        elements.append(render_typing_indicator())

    return elements

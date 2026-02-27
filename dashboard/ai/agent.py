"""
Gemini async agentic loop for the CBB dashboard chat.
Uses google-genai SDK with function calling.
Loops function_call → function_response until no more calls.
"""

from __future__ import annotations

import os
from datetime import date
from typing import Any

from dashboard.ai.tools import dispatch_tool, get_gemini_tools

MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
MAX_TOKENS = 4096
MAX_TOOL_ROUNDS = 10

_SYSTEM_PROMPT_TEMPLATE = """You are a knowledgeable NCAA Men's Division I college basketball analyst assistant.
You have access to live data including scores, box scores, play-by-play, rankings, and statistics.

TODAY'S DATE: {today}
YESTERDAY'S DATE: {yesterday}

When answering questions:
- ALWAYS call a tool to fetch current data — never answer from memory or training data.
- For any question about scores, games, or results you MUST call get_live_scores or get_games_by_date first.
- When the user says "yesterday", use date {yesterday}. When they say "today", use date {today}.
- Be concise and focused on what the user asked.
- Format stats clearly using markdown tables when appropriate.
- When a game is selected in the dashboard, you have context about that game and can reference it.

Your training data is outdated — always fetch fresh data via tools, never guess."""


def _build_system_prompt() -> str:
    today = date.today()
    yesterday = date.fromordinal(today.toordinal() - 1)
    return _SYSTEM_PROMPT_TEMPLATE.format(
        today=today.strftime("%Y-%m-%d"),
        yesterday=yesterday.strftime("%Y-%m-%d"),
    )


async def run_chat_turn(
    user_message: str,
    history: list[dict],
    context: dict[str, Any] | None = None,
) -> tuple[str, list[dict]]:
    """
    Run one turn of the Gemini agentic chat loop.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return (
            "GEMINI_API_KEY is not set. Please set it to enable AI chat.",
            history,
        )

    try:
        from google import genai
        from google.genai import types
        from google.api_core import exceptions
    except ImportError:
        return (
            "google-genai is not installed. Run: pip install -e '.[dashboard]'",
            history,
        )

    client = genai.Client(api_key=api_key)

    # ... (rest of the setup logic)
    full_user_message = user_message
    if context:
        ctx_parts = []
        if game_id := context.get("selected_game_id"):
            ctx_parts.append(f"[Context: The user is viewing game ID {game_id}]")
        if team := context.get("selected_team"):
            ctx_parts.append(f"[Context: The user is viewing {team}]")
        if prob_history := context.get("prob_history_json"):
            ctx_parts.append(f"[Context: Win probability history available. Call get_probability_history with game_id={context.get('selected_game_id')} and history_json={prob_history}]")
        if ctx_parts:
            full_user_message = "\n".join(ctx_parts) + "\n\n" + user_message

    contents = [
        types.Content(
            role=msg["role"],
            parts=[types.Part.from_text(text=p["text"]) for p in msg.get("parts", []) if p.get("text")],
        )
        for msg in history
        if msg.get("parts")
    ]
    contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text=full_user_message)])
    )

    tools = get_gemini_tools()
    config = types.GenerateContentConfig(
        system_instruction=_build_system_prompt(),
        tools=tools,
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="AUTO")
        ),
        max_output_tokens=MAX_TOKENS,
    )

    final_text = ""
    rounds = 0

    try:
        while rounds < MAX_TOOL_ROUNDS:
            rounds += 1

            response = await client.aio.models.generate_content(
                model=MODEL,
                contents=contents,
                config=config,
            )

            if not response.candidates:
                final_text = "No response from model."
                break

            candidate = response.candidates[0]
            model_content = candidate.content 

            text_parts = []
            function_calls = []

            for part in (model_content.parts or []):
                if hasattr(part, "text") and part.text:
                    text_parts.append(part.text)
                if hasattr(part, "function_call") and part.function_call:
                    function_calls.append(part.function_call)

            if text_parts:
                final_text += "".join(text_parts)

            contents.append(model_content)

            if not function_calls:
                break

            function_response_parts = []
            for fc in function_calls:
                tool_name = fc.name
                tool_args = dict(fc.args) if fc.args else {}
                result = await dispatch_tool(tool_name, tool_args)
                function_response_parts.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response={"output": result},
                    )
                )

            contents.append(
                types.Content(role="user", parts=function_response_parts)
            )

    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            final_text = (
                "⚠️ **API Quota Exceeded**\n\n"
                "I've hit the free-tier limit for the Gemini API. This usually resets after a few minutes.\n\n"
                "To fix this permanently, you can upgrade to a 'Pay-as-you-go' plan in Google AI Studio."
            )
        else:
            final_text = f"An error occurred: {str(e)}"

    if not final_text:
        final_text = "I couldn't generate a response. Please try again."

    updated_history = list(history) + [
        {"role": "user", "parts": [{"text": user_message}]},
        {"role": "model", "parts": [{"text": final_text}]},
    ]

    return final_text, updated_history

    if not final_text:
        final_text = "I couldn't generate a response. Please try again."

    # Build updated display history (text turns only, for rendering)
    updated_history = list(history) + [
        {"role": "user", "parts": [{"text": user_message}]},
        {"role": "model", "parts": [{"text": final_text}]},
    ]

    return final_text, updated_history


def _serialize_parts(parts) -> list[dict]:
    """Convert Gemini Part objects to JSON-serializable dicts."""
    result = []
    for part in (parts or []):
        if hasattr(part, "text") and part.text:
            result.append({"text": part.text})
        elif hasattr(part, "function_call") and part.function_call:
            result.append({
                "function_call": {
                    "name": part.function_call.name,
                    "args": dict(part.function_call.args or {}),
                }
            })
        elif hasattr(part, "function_response") and part.function_response:
            result.append({
                "function_response": {
                    "name": part.function_response.name,
                    "response": dict(part.function_response.response or {}),
                }
            })
    return result

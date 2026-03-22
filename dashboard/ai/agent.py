"""
Dual-backend agentic loop for CBB dashboard chat.
Supports Gemini (google-genai) and Ollama (OpenAI SDK).
Routes based on LLM_BACKEND env var.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date
from typing import Any

from dashboard.ai.tools import dispatch_tool, get_gemini_tools, get_openai_tools

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
LLM_BACKEND = os.environ.get("LLM_BACKEND", "gemini").lower()

MAX_TOKENS = 4096
MAX_TOOL_ROUNDS = 10

_SYSTEM_PROMPT_TEMPLATE = """You are a knowledgeable NCAA Men's Division I college basketball analyst assistant.
You have access to live data including scores, box scores, play-by-play, rankings, and statistics.

TODAY'S DATE: {today}
YESTERDAY'S DATE: {yesterday}

CRITICAL RULES (MUST FOLLOW):
1. **ALWAYS fetch fresh data** — NEVER answer from memory or training data alone.
2. **For ANY game-related question** (results, scores, standings, teams, stats, predictions):
   - FIRST call get_live_scores with date={today} to check TODAY's games
   - THEN call get_games_by_date with date={today} if needed
   - ONLY then answer the user
3. **For yesterday's games**, use get_live_scores with date={yesterday}
4. **For win probability questions**: MUST call get_win_probability, then explain_win_probability
5. **NEVER say "based on my knowledge"** — say "based on live data from [date]"

Examples of when to fetch:
- "Did Tennessee beat Alabama?" → Call get_live_scores({today}), then get_games_by_date({today})
- "What are the latest scores?" → Call get_live_scores({today}) immediately
- "Who won yesterday?" → Call get_live_scores({yesterday})
- "What's the win probability for game X?" → Call get_win_probability(game_id="X")

Be concise and focused on what the user asked.
Format stats clearly using markdown tables when appropriate.
When a game is selected in the dashboard, you have context about that game and can reference it."""


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
    Run one turn of the agentic chat loop.
    Routes to Gemini or Ollama based on LLM_BACKEND env var.
    """
    print(f"[Agent] run_chat_turn called: {user_message[:80]!r}", flush=True)
    print(f"[Agent] Using backend: {LLM_BACKEND}", flush=True)

    # Also log to a file for debugging
    with open(".agent_debug.log", "a", encoding="utf-8") as f:
        f.write(f"[{date.today()}] Backend: {LLM_BACKEND}\n")
        f.write(f"Message: {user_message[:80]}\n")

    if LLM_BACKEND == "ollama":
        return await _run_ollama_turn(user_message, history, context)
    else:
        return await _run_gemini_turn(user_message, history, context)


async def _run_gemini_turn(
    user_message: str,
    history: list[dict],
    context: dict[str, Any] | None = None,
) -> tuple[str, list[dict]]:
    """
    Run one turn of the Gemini agentic chat loop.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[Agent] ERROR: GEMINI_API_KEY not set!", flush=True)
        return (
            "GEMINI_API_KEY is not set. Please set it to enable AI chat.",
            history,
        )

    try:
        from google import genai
        from google.genai import types
        from google.api_core import exceptions
    except ImportError as ie:
        print(f"[Agent] ERROR: Import failed: {ie}", flush=True)
        return (
            "google-genai is not installed. Run: pip install -e '.[dashboard]'",
            history,
        )

    print(f"[Agent] Using Gemini model={GEMINI_MODEL}, key=...{api_key[-4:]}", flush=True)
    client = genai.Client(api_key=api_key)

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
            print(f"[Agent] Round {rounds}: calling Gemini...", flush=True)

            response = await client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=config,
            )
            print(f"[Agent] Round {rounds}: got response", flush=True)

            if not response.candidates:
                final_text = "No response from model."
                print(f"[Agent] No candidates in response", flush=True)
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
                print(f"[Agent] No tool calls, final response ready ({len(final_text)} chars)", flush=True)
                break

            for fc in function_calls:
                print(f"[Agent] Tool call: {fc.name}({dict(fc.args) if fc.args else {}})", flush=True)

            function_response_parts = []
            for fc in function_calls:
                tool_name = fc.name
                tool_args = dict(fc.args) if fc.args else {}
                result = await dispatch_tool(tool_name, tool_args)
                print(f"[Agent] Tool result for {tool_name}: {str(result)[:200]}", flush=True)
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
        print(f"[Agent] ERROR: {type(e).__name__}: {e}", flush=True)
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


async def _run_ollama_turn(
    user_message: str,
    history: list[dict],
    context: dict[str, Any] | None = None,
) -> tuple[str, list[dict]]:
    """
    Run one turn of the Ollama agentic chat loop using OpenAI SDK.
    """
    try:
        from openai import AsyncOpenAI
        import httpx
    except ImportError as ie:
        print(f"[Agent] ERROR: OpenAI SDK not installed: {ie}", flush=True)
        return (
            "OpenAI SDK is not installed. Run: pip install openai",
            history,
        )

    print(f"[Agent] Using Ollama model={OLLAMA_MODEL}, url={OLLAMA_BASE_URL}", flush=True)

    client = AsyncOpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

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

    messages = _convert_history_to_openai_format(history)
    messages.append({"role": "user", "content": full_user_message})

    tools = get_openai_tools()
    final_text = ""
    rounds = 0

    try:
        while rounds < MAX_TOOL_ROUNDS:
            rounds += 1
            print(f"[Agent] Round {rounds}: calling Ollama...", flush=True)

            response = await client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=MAX_TOKENS,
            )
            print(f"[Agent] Round {rounds}: got response", flush=True)

            if not response.choices:
                final_text = "No response from model."
                print(f"[Agent] No choices in response", flush=True)
                break

            choice = response.choices[0]

            if choice.message.content:
                final_text += choice.message.content

            messages.append({"role": "assistant", "content": choice.message.content or ""})

            if not choice.message.tool_calls:
                print(f"[Agent] No tool calls, final response ready ({len(final_text)} chars)", flush=True)
                break

            tool_results = []
            for tool_call in choice.message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}

                print(f"[Agent] Tool call: {tool_name}({tool_args})", flush=True)

                result = await dispatch_tool(tool_name, tool_args)
                print(f"[Agent] Tool result for {tool_name}: {str(result)[:200]}", flush=True)

                tool_results.append({
                    "type": "tool",
                    "tool_use_id": tool_call.id,
                    "content": json.dumps(result) if not isinstance(result, str) else result,
                })

            if tool_results:
                messages.append({
                    "role": "user",
                    "content": tool_results,
                })

    except Exception as e:
        print(f"[Agent] ERROR: {type(e).__name__}: {e}", flush=True)
        if "Could not connect" in str(e) or "ConnectError" in type(e).__name__:
            final_text = (
                "⚠️ **Ollama Not Running**\n\n"
                f"I couldn't connect to Ollama at `{OLLAMA_BASE_URL}`.\n\n"
                "Please make sure Ollama is running:\n"
                "1. Download from https://ollama.ai\n"
                "2. Run: `ollama pull llama3.1:8b`\n"
                "3. Ollama will start automatically at http://localhost:11434"
            )
        else:
            final_text = f"An error occurred: {str(e)[:200]}"

    if not final_text:
        final_text = "I couldn't generate a response. Please try again."

    updated_history = list(history) + [
        {"role": "user", "parts": [{"text": user_message}]},
        {"role": "model", "parts": [{"text": final_text}]},
    ]

    return final_text, updated_history


def _convert_history_to_openai_format(history: list[dict]) -> list[dict]:
    """Convert Gemini history format to OpenAI format."""
    messages = []
    for msg in history:
        if msg.get("parts"):
            content = ""
            for part in msg.get("parts", []):
                if part.get("text"):
                    content += part["text"]
            if content:
                role = "user" if msg.get("role") == "user" else "assistant"
                messages.append({"role": role, "content": content})
    return messages


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

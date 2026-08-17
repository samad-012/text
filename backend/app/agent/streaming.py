"""
Streaming variant of the agent loop, used only by app/routes/streaming.py.

Deliberately a SEPARATE function from run_turn() in agent.py, not a rewrite
of it — run_turn() is synchronous and already proven against the turn-based
route. This needs an async Groq client so token deltas can be consumed as
they arrive and sentence-flushed to TTS before the full reply exists, which
is a different execution model, not just a different style. Both functions
call the exact same TOOL_FUNCTIONS, TOOL_SCHEMAS, and SYSTEM_PROMPT, so tool
behaviour is identical across the two transports — only *when* things fire
differs.
"""

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from groq import AsyncGroq, RateLimitError as GroqRateLimitError
from openai import AsyncOpenAI, RateLimitError as OpenAIRateLimitError

from app.config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    HF_TOKEN,
    HF_MODEL,
)
from app.agent.agent import run_tool
from app.tools.registry import TOOL_SCHEMAS

logger = logging.getLogger(__name__)


# Primary LLM provider
async_client = AsyncGroq(api_key=GROQ_API_KEY)

# Hugging Face fallback LLM provider
hf_async_client = AsyncOpenAI(
    api_key=HF_TOKEN,
    base_url="https://router.huggingface.co/v1",
)


async def run_turn_streaming(
    history: list[dict[str, Any]],
    max_iterations: int = 5,
) -> AsyncIterator[dict[str, Any]]:
    """
    Yields: tool_call, tool_result, text_delta, done.

    text_delta events carry small raw token fragments — the caller (the WS
    route) buffers them into sentences before sending anything to TTS. This
    function has no opinion about sentence boundaries; that's a transport
    concern, not an agent concern.
    """

    for _ in range(max_iterations):
        try:
            stream = await async_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=history,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                stream=True,
            )

            logger.info(
                "LLM provider=groq model=%s",
                GROQ_MODEL,
            )

        except GroqRateLimitError as exc:
            logger.warning(
                "Groq rate limit reached; falling back to Hugging Face: %s",
                exc,
                exc_info=True,
            )

            try:
                stream = await hf_async_client.chat.completions.create(
                    model=HF_MODEL,
                    messages=history,
                    tools=TOOL_SCHEMAS,
                    tool_choice="auto",
                    stream=True,
                )

                logger.info(
                    "LLM provider=huggingface model=%s "
                    "fallback_reason=rate_limit",
                    HF_MODEL,
                )

            except OpenAIRateLimitError as hf_exc:
                logger.error(
                    "Hugging Face RateLimitError caught in "
                    "run_turn_streaming: %s",
                    hf_exc,
                    exc_info=True,
                )

                fallback = (
                    "I'm sorry, I'm temporarily unable to process that. "
                    "Please try again shortly."
                )

                history.append(
                    {
                        "role": "assistant",
                        "content": fallback,
                    }
                )

                yield {
                    "type": "text_delta",
                    "content": fallback,
                }

                yield {
                    "type": "done",
                }

                return

        text_buffer = ""

        # Tool-call fragments arrive spread across many chunks, keyed by
        # position in the array — the streaming delta format uses index as
        # the stable key until each tool call is complete.
        tool_calls_by_index: dict[int, dict[str, str]] = {}

        async for chunk in stream:
            delta = chunk.choices[0].delta

            if delta.content:
                text_buffer += delta.content

                yield {
                    "type": "text_delta",
                    "content": delta.content,
                }

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    slot = tool_calls_by_index.setdefault(
                        tc.index,
                        {
                            "id": "",
                            "name": "",
                            "arguments": "",
                        },
                    )

                    if tc.id:
                        slot["id"] = tc.id

                    if tc.function and tc.function.name:
                        slot["name"] += tc.function.name

                    if tc.function and tc.function.arguments:
                        slot["arguments"] += tc.function.arguments

        if not tool_calls_by_index:
            history.append(
                {
                    "role": "assistant",
                    "content": text_buffer,
                }
            )

            yield {
                "type": "done",
            }

            return

        # Assistant requested tools — same history bookkeeping as run_turn().
        history.append(
            {
                "role": "assistant",
                "content": text_buffer,
                "tool_calls": [
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": call["arguments"],
                        },
                    }
                    for call in tool_calls_by_index.values()
                ],
            }
        )

        for call in tool_calls_by_index.values():
            tool_name = call["name"]

            try:
                arguments = json.loads(
                    call["arguments"]
                )

            except json.JSONDecodeError as exc:
                result = {
                    "success": False,
                    "error": f"Invalid tool arguments: {exc}",
                }

                yield {
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "result": result,
                }

                history.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "name": tool_name,
                        "content": json.dumps(result),
                    }
                )

                continue

            yield {
                "type": "tool_call",
                "tool_name": tool_name,
                "arguments": arguments,
            }

            result = run_tool(
                tool_name,
                arguments,
            )

            yield {
                "type": "tool_result",
                "tool_name": tool_name,
                "result": result,
            }

            history.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "name": tool_name,
                    "content": json.dumps(result),
                }
            )

    fallback = (
        "I'm sorry, I wasn't able to complete that. "
        "Please try again."
    )

    history.append(
        {
            "role": "assistant",
            "content": fallback,
        }
    )

    yield {
        "type": "text_delta",
        "content": fallback,
    }

    yield {
        "type": "done",
    }
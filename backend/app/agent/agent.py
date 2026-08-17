import json
import logging
from datetime import date
from collections.abc import Iterator
from typing import Any

from groq import Groq, RateLimitError as GroqRateLimitError
from openai import OpenAI, RateLimitError as OpenAIRateLimitError

from app.config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    HF_TOKEN,
    HF_MODEL,
)
from app.tools.registry import TOOLS, TOOL_SCHEMAS

logger = logging.getLogger(__name__)


# Primary LLM provider
client = Groq(api_key=GROQ_API_KEY)

# Hugging Face fallback LLM provider
hf_client = OpenAI(
    api_key=HF_TOKEN,
    base_url="https://router.huggingface.co/v1",
)


SYSTEM_PROMPT = f"""
You are Ben, the voice reservation assistant for Saffron.

Today's restaurant date is {date.today().isoformat()}.

Your job is to help customers:
- check table availability
- make reservations
- retrieve reservations
- modify reservations
- cancel reservations
- answer basic restaurant questions

Use the provided tools whenever information or an action depends on restaurant data.

Never claim that a reservation was created, changed, retrieved, or cancelled unless the corresponding tool returned success.

Before creating a booking, make sure you have:
- customer name
- phone number
- date
- time
- party size

If any required information is missing, ask for it naturally. Never guess it.

Before booking a reservation:
1. Check availability.
2. Read back the reservation details.
3. Ask for confirmation.
4. Only call book_reservation after the customer confirms.

Before modifying a reservation, make sure you know which reservation the customer means.

Before cancelling a reservation:
1. Retrieve the reservation if necessary.
2. Read back the reservation details.
3. Ask for confirmation.
4. Only call cancel_reservation after the customer confirms.

Do not invent availability, reservation details, menu information, restaurant hours, or any other restaurant information.

If the user asks for something that the available tools cannot handle, politely explain that you cannot help with that request.

If you cannot understand the customer, politely ask them to repeat or clarify.

Keep spoken responses short, natural, and conversational.

Do not read JSON, tool names, function names, or implementation details aloud.
"""


TOOL_FUNCTIONS = {tool.__name__: tool for tool in TOOLS}


def run_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute a registered tool by name."""
    tool = TOOL_FUNCTIONS.get(tool_name)

    if tool is None:
        return {
            "success": False,
            "error": f"Unknown tool: {tool_name}",
        }

    try:
        return tool(**arguments)
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


def run_turn(
    history: list[dict[str, Any]],
    max_iterations: int = 5,
) -> Iterator[dict[str, Any]]:
    """
    Run one complete agent turn (non-streaming).

    Groq is the primary LLM provider.
    Hugging Face is used only when Groq hits a rate limit.

    Yields events for:
    - tool_call
    - tool_result
    - text
    - done
    """

    for _ in range(max_iterations):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=history,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
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
                response = hf_client.chat.completions.create(
                    model=HF_MODEL,
                    messages=history,
                    tools=TOOL_SCHEMAS,
                    tool_choice="auto",
                )

                logger.info(
                    "LLM provider=huggingface model=%s fallback_reason=rate_limit",
                    HF_MODEL,
                )

            except OpenAIRateLimitError as hf_exc:
                logger.error(
                    "Hugging Face RateLimitError: %s",
                    hf_exc,
                    exc_info=True,
                )

                fallback_message = (
                    "I'm sorry, I'm temporarily unable to process your request. "
                    "Please try again in a few minutes."
                )

                history.append(
                    {
                        "role": "assistant",
                        "content": fallback_message,
                    }
                )

                yield {
                    "type": "text",
                    "content": fallback_message,
                }

                yield {
                    "type": "done",
                }

                return

        assistant_message = response.choices[0].message

        # No tool call -> final assistant response
        if not assistant_message.tool_calls:
            content = assistant_message.content or ""

            history.append(
                {
                    "role": "assistant",
                    "content": content,
                }
            )

            yield {
                "type": "text",
                "content": content,
            }

            yield {
                "type": "done",
            }

            return

        # Assistant requested tools
        assistant_message_dict = {
            "role": "assistant",
            "content": assistant_message.content or "",
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in assistant_message.tool_calls
            ],
        }

        history.append(assistant_message_dict)

        # Execute tool calls
        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name

            try:
                arguments = json.loads(
                    tool_call.function.arguments
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
                        "tool_call_id": tool_call.id,
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
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": json.dumps(result),
                }
            )

    # Safety limit reached
    fallback_message = (
        "I'm sorry, I wasn't able to complete that request. "
        "Please try again."
    )

    history.append(
        {
            "role": "assistant",
            "content": fallback_message,
        }
    )

    yield {
        "type": "text",
        "content": fallback_message,
    }

    yield {
        "type": "done",
    }
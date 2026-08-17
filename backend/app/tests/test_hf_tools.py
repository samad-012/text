import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from app.config import HF_MODEL
from app.tools.registry import TOOL_SCHEMAS

load_dotenv()

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.environ["HF_TOKEN"],
)

print("=== CONFIG ===")
print("Model:", HF_MODEL)
print("Number of tools:", len(TOOL_SCHEMAS))

print("\n=== TOOLS ===")
for tool in TOOL_SCHEMAS:
    print(tool["function"]["name"])

response = client.chat.completions.create(
    model=HF_MODEL,
    messages=[
        {
            "role": "system",
            "content": (
                "You are a restaurant reservation assistant. "
                "Use the provided tools whenever the user asks "
                "about restaurant reservations."
            ),
        },
        {
            "role": "user",
            "content": "I need a table for four tomorrow at 8pm.",
        },
    ],
    tools=TOOL_SCHEMAS,
    tool_choice="auto",
)

message = response.choices[0].message

print("\n=== RAW RESPONSE ===")
print(response)

print("\n=== TOOL CALLS ===")

if not message.tool_calls:
    print("NO TOOL CALL WAS GENERATED")
    raise SystemExit(1)

for tool_call in message.tool_calls:
    print("\nTool:", tool_call.function.name)
    print("Arguments:", tool_call.function.arguments)

    try:
        arguments = json.loads(tool_call.function.arguments)

        print("Parsed JSON:", arguments)
        print("VALID TOOL CALL JSON: YES")

    except json.JSONDecodeError as exc:
        print("VALID TOOL CALL JSON: NO")
        print("JSON error:", exc)
        raise SystemExit(1)

print("\n=== RESULT ===")
print("HF MODEL + YOUR REAL TOOL SCHEMAS: PASS")
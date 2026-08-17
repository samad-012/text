# scripts/test_stream.py
import asyncio
from app.agent.agent import SYSTEM_PROMPT
from app.agent.streaming import run_turn_streaming

history = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": "table for four tomorrow at 8pm"}]

async def main():
    async for event in run_turn_streaming(history):
        print(event)

if __name__ == "__main__":
    asyncio.run(main())
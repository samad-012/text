# scripts/test_tts_stream.py
import asyncio
from app.speech.tts_stream import DeepgramTTSStream

async def main():
    tts = DeepgramTTSStream()
    await tts.connect()
    total_bytes = 0
    async for chunk in tts.speak("Your reservation is confirmed for tomorrow at eight p.m."):
        total_bytes += len(chunk)
        print(f"got chunk: {len(chunk)} bytes (total {total_bytes})")

    await tts.close()

if __name__ == "__main__":
    asyncio.run(main())
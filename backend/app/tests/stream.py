# scripts/stream.py
import asyncio
import json

import numpy as np
import soundfile as sf
import websockets


async def main(wav_path: str):
    audio, sr = sf.read(wav_path, dtype="int16")
    if audio.ndim > 1:
        audio = audio[:, 0]
    assert sr == 16000, "resample to 16kHz first (ffmpeg -ar 16000)"

    async with websockets.connect("ws://localhost:8000/ws/stream?session_id=wstest1") as ws:

        async def sender():
            chunk_samples = int(sr * 0.1)
            for i in range(0, len(audio), chunk_samples):
                await ws.send(audio[i : i + chunk_samples].tobytes())
                await asyncio.sleep(0.1)
            await asyncio.sleep(1.5)  # let trailing silence register
            await ws.send(json.dumps({"type": "end"}))

        async def receiver():
            audio_out = bytearray()
            try:
                async for msg in ws:
                    if isinstance(msg, bytes):
                        audio_out.extend(msg)
                    else:
                        print(json.loads(msg))
            except websockets.exceptions.ConnectionClosed:
                pass  # Server closed connection

            if audio_out:
                sf.write(
                    "ws_reply.wav",
                    np.frombuffer(bytes(audio_out), dtype=np.int16),
                    24000,
                )
                print(f"wrote ws_reply.wav ({len(audio_out)} bytes)")

        # Run both the sender and receiver concurrently inside the WebSocket connection context
        await asyncio.gather(sender(), receiver())


if __name__ == "__main__":
    import sys

    asyncio.run(main(sys.argv[1]))
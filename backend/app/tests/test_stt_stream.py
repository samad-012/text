# scripts/test_stt_stream.py
"""
Feeds a wav file into DeepgramSTTStream in simulated real-time chunks
(as if it were live mic audio) and prints transcript events as they arrive.

Usage: python -m scripts.test_stt_stream path/to/clip.wav
"""
import asyncio
import sys

import numpy as np
import soundfile as sf

from app.speech.stt_stream import DeepgramSTTStream

CHUNK_MS = 100  # send ~100ms of audio at a time, like a real mic stream would


async def main(wav_path: str):
    audio, sample_rate = sf.read(wav_path, dtype="int16")
    if audio.ndim > 1:
        audio = audio[:, 0]  # force mono

    if sample_rate != 16000:
        # naive resample via linear interpolation - fine for testing, not for production
        duration = len(audio) / sample_rate
        target_len = int(duration * 16000)
        audio = np.interp(
            np.linspace(0, len(audio), target_len),
            np.arange(len(audio)),
            audio,
        ).astype(np.int16)
        sample_rate = 16000

    stt = DeepgramSTTStream()
    await stt.connect()

    async def send_audio_task():
        chunk_samples = int(sample_rate * CHUNK_MS / 1000)
        for i in range(0, len(audio), chunk_samples):
            chunk = audio[i : i + chunk_samples].tobytes()
            await stt.send_audio(chunk)
            await asyncio.sleep(CHUNK_MS / 1000)  # simulate real-time pacing
        await stt.close()

    async def print_events_task():
        async for event in stt.events():
            if event.get("type") == "Results":
                alt = event["channel"]["alternatives"][0]
                if alt["transcript"]:
                    tag = "FINAL" if event.get("speech_final") else "interim"
                    print(f"[{tag}] {alt['transcript']}")
            elif event.get("type") == "UtteranceEnd":
                print("[UtteranceEnd]")

    await asyncio.gather(send_audio_task(), print_events_task())


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
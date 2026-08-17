import httpx

from app.config import DEEPGRAM_API_KEY, DEEPGRAM_TTS_MODEL

_TTS_URL = "https://api.deepgram.com/v1/speak"


def synthesize(text: str) -> bytes:
    """Return mp3 audio bytes for the given text."""
    response = httpx.post(
        _TTS_URL,
        params={"model": DEEPGRAM_TTS_MODEL},
        headers={
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"text": text},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.content
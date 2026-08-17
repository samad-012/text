"""
Deepgram Aura-2 streaming TTS client.

One connection is opened per assistant TURN (not per sentence), so Aura
keeps prosody consistent across sentence-flushed chunks instead of
restarting cold on every sentence. Call `speak(sentence)` once per completed
sentence; it yields mp3 bytes as Deepgram produces them.
"""
import json
import logging
from typing import AsyncIterator

import websockets

from app.config import DEEPGRAM_API_KEY, DEEPGRAM_TTS_MODEL

logger = logging.getLogger(__name__)

_TTS_URL = (
    "wss://api.deepgram.com/v1/speak"
    f"?model={DEEPGRAM_TTS_MODEL}"
    "&encoding=linear16"
    "&sample_rate=16000"
    "&container=none"
)


def pcm_to_wav(pcm_data: bytes, sample_rate: int = 16000, channels: int = 1, bit_depth: int = 16) -> bytes:
    """Prepends a 44-byte WAV header to raw PCM data, dynamically calculating size fields."""
    file_size = 36 + len(pcm_data)
    byte_rate = sample_rate * channels * (bit_depth // 8)
    block_align = channels * (bit_depth // 8)
    
    header = bytearray()
    header.extend(b'RIFF')
    header.extend(file_size.to_bytes(4, 'little'))
    header.extend(b'WAVE')
    header.extend(b'fmt ')
    header.extend((16).to_bytes(4, 'little'))  # Subchunk1Size (16 for PCM)
    header.extend((1).to_bytes(2, 'little'))   # AudioFormat (1 for PCM)
    header.extend(channels.to_bytes(2, 'little'))
    header.extend(sample_rate.to_bytes(4, 'little'))
    header.extend(byte_rate.to_bytes(4, 'little'))
    header.extend(block_align.to_bytes(2, 'little'))
    header.extend(bit_depth.to_bytes(2, 'little'))
    header.extend(b'data')
    header.extend(len(pcm_data).to_bytes(4, 'little'))
    return bytes(header) + pcm_data


class DeepgramTTSStream:
    def __init__(self) -> None:
        self._ws: websockets.WebSocketClientProtocol | None = None

    async def connect(self) -> None:
        logger.info(f"Connecting to Deepgram TTS: {_TTS_URL}")
        self._ws = await websockets.connect(
            _TTS_URL,
            additional_headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"},
        )
        logger.info("Connected to Deepgram TTS WebSocket.")

    async def speak(self, text: str) -> AsyncIterator[bytes]:
        """
        Send one sentence, flush it, and yield audio chunks until Aura
        confirms the flush drained ("Flushed"). Safe to call repeatedly on
        the same connection for successive sentences within one turn.
        """
        if self._ws is None:
            raise RuntimeError("call connect() first")

        logger.info(f"Sending text to TTS: {repr(text)}")
        await self._ws.send(json.dumps({"type": "Speak", "text": text}))
        await self._ws.send(json.dumps({"type": "Flush"}))

        while True:
            raw = await self._ws.recv()
            if isinstance(raw, bytes):
                # Wrap PCM bytes in a WAV container chunk before yielding to the client
                yield pcm_to_wav(raw, sample_rate=16000)
                continue
            
            # Text frames here are control/metadata messages, not audio.
            msg = json.loads(raw)
            msg_type = msg.get("type")
            if msg_type == "Flushed":
                logger.info("TTS flush drained.")
                return  # this sentence's audio is fully drained
            elif msg_type == "Error":
                logger.error(f"Deepgram TTS protocol error: {msg}")
            else:
                logger.warning(f"Unexpected Deepgram TTS control message: {msg}")

    async def close(self) -> None:
        if self._ws is not None:
            try:
                logger.info("Closing Deepgram TTS connection.")
                await self._ws.send(json.dumps({"type": "Close"}))
                await self._ws.close()
            except Exception as exc:
                logger.error(f"Error closing Deepgram TTS WebSocket: {exc}")
            finally:
                self._ws = None
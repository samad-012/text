"""
Deepgram Nova-3 streaming STT client.

Wraps a live WebSocket connection to Deepgram. The rest of the app doesn't
need to know anything about Deepgram's wire protocol — it just calls
`send_audio()` with raw PCM16 frames and iterates `listen()` for transcripts.

Uses raw `websockets` rather than deepgram-sdk on purpose: one fewer
dependency, and every line here is something you can explain in the
interview without pointing at SDK internals.
"""
import json
import logging
from typing import AsyncIterator

import websockets

from app.config import DEEPGRAM_API_KEY, DEEPGRAM_STT_MODEL

logger = logging.getLogger(__name__)

_STT_URL = (
    "wss://api.deepgram.com/v1/listen"
    f"?model={DEEPGRAM_STT_MODEL}"
    "&encoding=linear16"
    "&sample_rate=16000"
    "&channels=1"
    "&interim_results=true"
    "&endpointing=300"
    "&utterance_end_ms=1000"
    "&smart_format=true"
)


class DeepgramSTTStream:
    """One instance per caller session (per WebSocket connection)."""

    def __init__(self) -> None:
        self._ws: websockets.WebSocketClientProtocol | None = None

    async def connect(self) -> None:
        logger.info(f"Connecting to Deepgram STT: {_STT_URL}")
        self._ws = await websockets.connect(
            _STT_URL,
            additional_headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"},
        )
        logger.info("Connected to Deepgram STT WebSocket.")

    async def send_audio(self, pcm16_bytes: bytes) -> None:
        """Forward one chunk of raw PCM16 audio to Deepgram."""
        if self._ws is None:
            raise RuntimeError("call connect() first")
        await self._ws.send(pcm16_bytes)

    async def listen(self) -> AsyncIterator[dict]:
        """
        Yields parsed events as Deepgram sends them:
          {"type": "transcript", "text": str, "is_final": bool, "speech_final": bool}
          {"type": "utterance_end"}

        speech_final=True is Deepgram's own endpointing decision (server-side
        VAD + silence detection) — that's the trigger to run the agent, not a
        client-side timer. is_final=True without speech_final just means one
        recognition window closed; the utterance may still be continuing.
        """
        if self._ws is None:
            raise RuntimeError("call connect() first")
        async for raw in self._ws:
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "Results":
                alt = msg["channel"]["alternatives"][0]
                text = alt.get("transcript", "")
                if not text:
                    continue
                yield {
                    "type": "transcript",
                    "text": text,
                    "is_final": msg.get("is_final", False),
                    "speech_final": msg.get("speech_final", False),
                }
            elif msg_type == "UtteranceEnd":
                yield {"type": "utterance_end"}
            elif msg_type == "Error":
                logger.error(f"Deepgram STT protocol error: {msg}")
            else:
                logger.warning(f"Unexpected Deepgram STT message type {msg_type}: {msg}")

    async def close(self) -> None:
        if self._ws is not None:
            try:
                logger.info("Closing Deepgram STT connection.")
                # Tells Deepgram we're done sending audio; flushes anything buffered.
                await self._ws.send(json.dumps({"type": "CloseStream"}))
                await self._ws.close()
            except Exception as exc:
                logger.error(f"Error closing Deepgram STT WebSocket: {exc}")
            finally:
                self._ws = None
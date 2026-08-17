"""
WS /ws/stream — the duplex streaming voice mode.

Same job as turn_based.py (STT -> agent -> TTS), but everything happens
concurrently instead of sequentially: audio is transcribed as it arrives,
the reply is spoken sentence-by-sentence as it's generated, and the caller
can interrupt mid-reply. Turn-based commits to a turn boundary via a UI
button (trivially correct); here the boundary is inferred from Deepgram's
endpointing (`speech_final`), which is where the real complexity lives.
"""
import asyncio
import logging
import re
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agent.streaming import run_turn_streaming
from app.core.sessions import get_history
from app.speech.stt_stream import DeepgramSTTStream
from app.speech.tts_stream import DeepgramTTSStream

logger = logging.getLogger(__name__)

router = APIRouter()

_SENTENCE_END = re.compile(r"[.!?]\s*$")
_MAX_BUFFER_CHARS = 60  # flush mid-sentence past this length, for time-to-first-audio


@router.websocket("/ws/stream")
async def stream(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client WebSocket connected to /ws/stream")

    session_id = websocket.query_params.get("session_id") or str(uuid.uuid4())
    history = get_history(session_id)
    await websocket.send_json({"type": "session", "session_id": session_id})

    stt = DeepgramSTTStream()
    await stt.connect()

    current_turn_task: asyncio.Task | None = None

    async def pump_client_audio() -> None:
        """Client mic frames (raw PCM16, from the AudioWorklet) -> Deepgram."""
        while True:
            message = await websocket.receive()
            if "bytes" in message:
                await stt.send_audio(message["bytes"])
            elif "text" in message:
                logger.info(f"Received text frame from client WS: {message['text']}")
                # If test script sends an end signal, we can optionally handle it or log it
            else:
                # If we get a disconnect type, websocket.receive() will raise WebSocketDisconnect
                break

    async def run_one_turn(user_text: str) -> None:
        """Everything that happens once we've decided the user finished speaking."""
        history.append({"role": "user", "content": user_text})

        tts = DeepgramTTSStream()
        await tts.connect()
        sentence_buffer = ""

        try:
            async for event in run_turn_streaming(history):
                if event["type"] == "tool_call":
                    await websocket.send_json(
                        {"type": "tool_call", "tool": event["tool_name"], "arguments": event["arguments"]}
                    )
                elif event["type"] == "tool_result":
                    await websocket.send_json(
                        {"type": "tool_result", "tool": event["tool_name"], "result": event["result"]}
                    )
                elif event["type"] == "text_delta":
                    sentence_buffer += event["content"]
                    await websocket.send_json({"type": "text_delta", "content": event["content"]})

                    if _SENTENCE_END.search(sentence_buffer) or len(sentence_buffer) >= _MAX_BUFFER_CHARS:
                        chunk_to_speak, sentence_buffer = sentence_buffer, ""
                        async for audio_chunk in tts.speak(chunk_to_speak):
                            await websocket.send_bytes(audio_chunk)
                elif event["type"] == "done":
                    if sentence_buffer.strip():
                        async for audio_chunk in tts.speak(sentence_buffer):
                            await websocket.send_bytes(audio_chunk)
                    await websocket.send_json({"type": "turn_done"})
        except asyncio.CancelledError:
            # Barge-in: the user started talking again mid-reply. We do NOT
            # try to reconstruct "what Aura actually finished saying" back
            # into history — our side only knows what text we *sent* to TTS,
            # not how much of the audio the client had played before it got
            # the barge_in message and cleared its queue. Left as an honest
            # simplification: history keeps whatever was appended by
            # run_turn_streaming up to the cancel point (completed tool
            # calls/results survive; the in-flight assistant text does not).
            raise
        finally:
            await tts.close()

    async def pump_transcripts() -> None:
        nonlocal current_turn_task
        async for event in stt.listen():
            if event["type"] != "transcript":
                continue

            if not event["is_final"]:
                # Any speech arriving while the agent is talking = barge-in.
                if current_turn_task is not None and not current_turn_task.done():
                    logger.info("Barge-in detected! Cancelling assistant speech turn task.")
                    current_turn_task.cancel()
                    await websocket.send_json({"type": "barge_in"})
                await websocket.send_json({"type": "interim", "text": event["text"]})
                continue

            if event["speech_final"] and event["text"].strip():
                logger.info(f"Speech final transcript detected: {repr(event['text'])}")
                if current_turn_task is not None and not current_turn_task.done():
                    logger.info("Cancelling current turn task for a new speech turn.")
                    current_turn_task.cancel()
                current_turn_task = asyncio.create_task(run_one_turn(event["text"]))

    try:
        await asyncio.gather(pump_client_audio(), pump_transcripts())
    except WebSocketDisconnect:
        pass
    finally:
        if current_turn_task is not None:
            current_turn_task.cancel()
        await stt.close()
import base64
import uuid

from fastapi import APIRouter, Form, UploadFile
from pydantic import BaseModel

from app.agent.agent import run_turn
from app.core.sessions import get_history
from app.speech.stt import transcribe
from app.speech.tts import synthesize

router = APIRouter()


class TurnResponse(BaseModel):
    session_id: str
    transcript: str
    reply: str
    tool_calls: list[dict]
    audio_base64: str


@router.post("/turn", response_model=TurnResponse)
def turn(audio: UploadFile, session_id: str | None = Form(default=None)):
    session_id = session_id or str(uuid.uuid4())
    history = get_history(session_id)

    audio_bytes = audio.file.read()
    transcript = transcribe(audio_bytes, filename=audio.filename or "audio.webm")

    tool_trace: list[dict] = []

    if not transcript:
        reply_text = "Sorry, I didn't catch that — could you say that again?"
        history.append({"role": "assistant", "content": reply_text})
    else:
        history.append({"role": "user", "content": transcript})
        reply_text = ""
        for event in run_turn(history):
            if event["type"] == "tool_call":
                tool_trace.append({"tool": event["tool_name"], "arguments": event["arguments"]})
            elif event["type"] == "tool_result":
                for entry in reversed(tool_trace):
                    if entry["tool"] == event["tool_name"] and "result" not in entry:
                        entry["result"] = event["result"]
                        break
            elif event["type"] == "text":
                reply_text = event["content"]

    audio_out = synthesize(reply_text) if reply_text else b""

    return TurnResponse(
        session_id=session_id,
        transcript=transcript,
        reply=reply_text,
        tool_calls=tool_trace,
        audio_base64=base64.b64encode(audio_out).decode("ascii"),
    )
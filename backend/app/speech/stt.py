import io

from groq import Groq

from app.config import GROQ_API_KEY, GROQ_STT_MODEL

client = Groq(api_key=GROQ_API_KEY)


def transcribe(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """Transcribe a full audio clip and return plain text."""
    file_obj = io.BytesIO(audio_bytes)
    file_obj.name = filename  # SDK reads the extension to infer format

    result = client.audio.transcriptions.create(
        file=file_obj,
        model=GROQ_STT_MODEL,
        response_format="text",
    )
    text = result if isinstance(result, str) else getattr(result, "text", "")
    return text.strip()
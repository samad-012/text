import os

from dotenv import load_dotenv


load_dotenv()


GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile",
)

GROQ_STT_MODEL = os.environ.get(
    "GROQ_STT_MODEL",
    "whisper-large-v3-turbo",
)


# Hugging Face fallback LLM
HF_TOKEN = os.environ.get("HF_TOKEN", "")
HF_MODEL = os.environ.get(
    "HF_MODEL",
    "openai/gpt-oss-120b:cerebras",
)


DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
DEEPGRAM_TTS_MODEL = os.environ.get(
    "DEEPGRAM_TTS_MODEL",
    "aura-2-thalia-en",
)
DEEPGRAM_STT_MODEL = os.environ.get(
    "DEEPGRAM_STT_MODEL",
    "nova-3",
)
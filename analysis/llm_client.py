import logging

from google import genai
from google.genai import types

from config import settings

logger = logging.getLogger(__name__)

_client: genai.Client | None = None

_SYSTEM = "You are a professional financial analyst. Be concise and data-driven."
DEFAULT_MODEL = "gemini-2.0-flash"


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def chat(prompt: str, system: str = "", model: str = DEFAULT_MODEL) -> str:
    client = get_client()
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system or _SYSTEM,
            max_output_tokens=2048,
        ),
    )
    return response.text

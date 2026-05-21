import logging

from groq import Groq

from config import settings

logger = logging.getLogger(__name__)

_client: Groq | None = None

_SYSTEM = "You are a professional financial analyst. Be concise and data-driven."
DEFAULT_MODEL = "llama-3.3-70b-versatile"


def get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def chat(prompt: str, system: str = "", model: str = DEFAULT_MODEL) -> str:
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        max_tokens=2048,
        messages=[
            {"role": "system", "content": system or _SYSTEM},
            {"role": "user",   "content": prompt},
        ],
    )
    return response.choices[0].message.content

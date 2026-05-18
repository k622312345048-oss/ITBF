import logging

import anthropic

from config import settings

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def chat(prompt: str, system: str = "", model: str = "claude-opus-4-7") -> str:
    client = get_client()
    messages = [{"role": "user", "content": prompt}]
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system or "You are a professional financial analyst. Be concise and data-driven.",
        messages=messages,
    )
    return response.content[0].text

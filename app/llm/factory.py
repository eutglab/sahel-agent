from __future__ import annotations

from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.base import LLMClient
from app.llm.providers.mock import MockLLMClient

logger = get_logger("sahel.llm")

_CACHE: dict[str, LLMClient] = {}


def get_llm_client(provider: Optional[str] = None) -> LLMClient:
    """Return an LLM client for the requested (or configured) provider.

    Never raises: an unknown or broken provider falls back to the mock so the
    agent always has a working reasoning path.
    """
    name = (provider or settings.llm_provider or "mock").lower()
    if name in _CACHE:
        return _CACHE[name]

    client: LLMClient
    if name == "mock":
        client = MockLLMClient()
    elif name == "anthropic":
        try:
            from app.llm.providers.anthropic import AnthropicLLMClient

            client = AnthropicLLMClient()
        except Exception as exc:  # noqa: BLE001
            logger.warning("anthropic client unavailable (%s); using mock", exc)
            client = MockLLMClient()
    elif name == "openai":
        try:
            from app.llm.providers.openai import OpenAILLMClient

            client = OpenAILLMClient()
        except Exception as exc:  # noqa: BLE001
            logger.warning("openai client unavailable (%s); using mock", exc)
            client = MockLLMClient()
    elif name == "hackathon":
        try:
            from app.llm.providers.hackathon import HackathonLLMClient

            client = HackathonLLMClient()
        except Exception as exc:  # noqa: BLE001
            logger.warning("hackathon client unavailable (%s); using mock", exc)
            client = MockLLMClient()
    else:
        logger.warning("unknown LLM provider '%s'; using mock", name)
        client = MockLLMClient()

    _CACHE[name] = client
    return client


def reset_cache() -> None:
    _CACHE.clear()

"""OpenRouter adapter — optional LLM provider (https://openrouter.ai).

INTEGRATION_READY: active only when ``OPENROUTER_API_KEY`` **and**
``OPENROUTER_MODEL`` are both set, and the ``openai`` package is installed.
OpenRouter's chat-completions endpoint is OpenAI-compatible, so this is a
thin adapter around ``OpenAILLMClient`` (same shape as ``HackathonLLMClient``)
rather than a new SDK integration.

No model is assumed available by default — OpenRouter's catalogue changes
over time, so guessing one risks a silent 404. Pick a currently available
model id from https://openrouter.ai/models and set ``OPENROUTER_MODEL``; until
then this provider reports itself NOT CONFIGURED and the fallback chain moves
on to the deterministic planner / mock, exactly like an unconfigured
Anthropic/OpenAI provider.

Like every other real provider, this one is only ever reached when
``settings.offline_first`` is False (see ``app/agent/agent.py`` and
``app/agent/assistant.py``) — DEMO_MODE / ENVIRONMENT=demo always short-circuits
to the mock client before this provider's network code runs.
"""
from __future__ import annotations

from app.core.config import get_secret, settings
from app.core.errors import ProviderUnavailable
from app.core.schemas import HealthState, HealthStatus, MaturityStatus

from app.llm.providers.openai import OpenAILLMClient


class OpenRouterLLMClient(OpenAILLMClient):
    name = "openrouter"
    status = MaturityStatus.INTEGRATION_READY

    def __init__(self) -> None:
        # Deliberately not calling OpenAILLMClient.__init__ with model=None:
        # that constructor falls back to settings.openai_model ("gpt-4o-mini"),
        # which is the wrong default for OpenRouter's namespaced model ids
        # (e.g. "openai/gpt-4o-mini"). No fallback here — see module docstring.
        self._base_url = settings.openrouter_base_url or "https://openrouter.ai/api/v1"
        self._key = get_secret("OPENROUTER_API_KEY")
        self._model = settings.openrouter_model
        self._timeout = settings.openrouter_timeout_seconds

    def _client(self):
        if not self._key:
            raise ProviderUnavailable("OPENROUTER_API_KEY not set")
        if not self._model:
            raise ProviderUnavailable(
                "OPENROUTER_MODEL not set — pick a currently available model id "
                "from https://openrouter.ai/models"
            )
        return super()._client()

    def health_check(self) -> HealthStatus:
        if not self._key:
            return HealthStatus(
                component="llm:openrouter", state=HealthState.WARNING,
                detail="OPENROUTER_API_KEY not set (INTEGRATION_READY)", provider=self.name,
            )
        if not self._model:
            return HealthStatus(
                component="llm:openrouter", state=HealthState.WARNING,
                detail="OPENROUTER_MODEL not set — choose a model (see .env.example)", provider=self.name,
            )
        import importlib.util

        if importlib.util.find_spec("openai") is None:
            return HealthStatus(
                component="llm:openrouter", state=HealthState.WARNING,
                detail="key set but `openai` package not installed", provider=self.name,
            )
        return HealthStatus(
            component="llm:openrouter", state=HealthState.READY,
            detail=f"key set, model {self._model}", provider=self.name,
        )

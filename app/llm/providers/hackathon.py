"""Generic hackathon LLM endpoint (assumed OpenAI-compatible).

INTEGRATION_READY. On the day: set HACKATHON_LLM_BASE_URL, HACKATHON_LLM_API_KEY,
HACKATHON_LLM_MODEL, then LLM_PROVIDER=hackathon. If the organiser's API is not
OpenAI-compatible, subclass and override the three methods.
"""
from __future__ import annotations

from app.core.config import settings
from app.core.errors import NotIntegratedError
from app.core.schemas import HealthState, HealthStatus, MaturityStatus

from app.llm.providers.openai import OpenAILLMClient


class HackathonLLMClient(OpenAILLMClient):
    name = "hackathon"
    status = MaturityStatus.INTEGRATION_READY

    def __init__(self) -> None:
        super().__init__(
            base_url=settings.hackathon_llm_base_url or None,
            api_key_env="HACKATHON_LLM_API_KEY",
            model=settings.hackathon_llm_model or "hackathon-model",
            provider_name="hackathon",
        )

    def _client(self):
        if not settings.hackathon_llm_base_url or not self._key:
            raise NotIntegratedError(
                "hackathon LLM not configured (set HACKATHON_LLM_BASE_URL + HACKATHON_LLM_API_KEY + HACKATHON_LLM_MODEL)"
            )
        return super()._client()

    def health_check(self) -> HealthStatus:
        if not settings.hackathon_llm_base_url or not self._key:
            return HealthStatus(
                component="llm:hackathon",
                state=HealthState.WARNING,
                detail="not configured (INTEGRATION_READY)",
                provider=self.name,
            )
        return HealthStatus(
            component="llm:hackathon",
            state=HealthState.WARNING,
            detail="configured but unverified — run test_integrations.py",
            provider=self.name,
        )

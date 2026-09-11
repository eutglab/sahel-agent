from __future__ import annotations

import json
from typing import Any, Dict

from pydantic import BaseModel

from app.core.config import settings
from app.core.errors import ProviderError, ProviderUnavailable
from app.core.schemas import HealthState, HealthStatus, MaturityStatus
from app.llm.factory import get_llm_client
from app.tools.base import BaseProvider
from app.tools.recommendation.providers.template import synthesize
from app.tools.recommendation.schema import RecommendationInput, RecommendationOutput

_SYSTEM = (
    "You are the synthesis step of an environmental decision-support agent. You receive "
    "STRUCTURED tool outputs only. Do not invent numbers. Produce STRICT JSON matching: "
    "{priority: 'low'|'medium'|'high', main_finding: str, recommended_actions: [str], "
    "monitoring_actions: [str], warnings: [str], confidence: 0..1, limitations: [str]}. "
    "Use cautious language. Always include a warning that this is decision support, not "
    "validated agronomic advice."
)


class LLMRecommendationProvider(BaseProvider):
    """Real synthesis via the configured LLM, grounded on structured inputs.

    INTEGRATION_READY. Falls through to the deterministic template if the model
    output is unusable, so the tool contract always holds.
    """

    name = "llm"
    status = MaturityStatus.INTEGRATION_READY
    requires_credentials = True

    def run(self, payload: BaseModel) -> Dict[str, Any]:
        assert isinstance(payload, RecommendationInput)
        client = get_llm_client()
        if client.is_mock:
            raise ProviderUnavailable("no real LLM provider active for recommendation")
        if settings.offline_first:
            raise ProviderUnavailable("offline/demo mode — real LLM synthesis skipped")

        user = "STRUCTURED INPUTS:\n" + json.dumps(payload.model_dump(), default=str)[:6000]
        try:
            resp = client.complete(_SYSTEM, user, max_tokens=900)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"llm recommendation call failed: {exc}") from exc

        data = _parse_json(resp.text)
        if not data:
            raise ProviderError("llm recommendation returned unparseable output")
        # Backfill any missing required keys from the deterministic synthesis.
        base = synthesize(payload)
        for key in ("priority", "main_finding", "confidence"):
            data.setdefault(key, base[key])
        for key in ("recommended_actions", "monitoring_actions", "warnings", "limitations",
                    "evidence", "evidence_source"):
            data.setdefault(key, base[key])
        data["method"] = f"llm synthesis ({client.name}), grounded on structured tool outputs"
        return RecommendationOutput.model_validate(data).model_dump()

    def health_check(self) -> HealthStatus:
        client = get_llm_client()
        if client.is_mock:
            return HealthStatus(
                component="provider:llm",
                state=HealthState.WARNING,
                detail="no real LLM provider active (INTEGRATION_READY)",
                provider=self.name,
            )
        return HealthStatus(
            component="provider:llm",
            state=HealthState.READY,
            detail=f"using LLM provider '{client.name}'",
            provider=self.name,
        )


def _parse_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}

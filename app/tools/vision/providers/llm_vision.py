from __future__ import annotations

import json
from typing import Any, Dict

from pydantic import BaseModel

from app.core.config import settings
from app.core.errors import ProviderError, ProviderUnavailable
from app.core.schemas import HealthState, HealthStatus, MaturityStatus
from app.llm.factory import get_llm_client
from app.tools.base import BaseProvider
from app.tools.vision.schema import VisionInput, VisionOutput

_PROMPT = (
    "You are assisting an environmental decision-support tool. Look at this plant/field "
    "photo and return STRICT JSON with keys: observations (list of short factual strings), "
    "possible_signs (list; use cautious wording like 'possible', 'compatible with'), "
    "confidence (0..1), limitations (list). Do NOT give a definitive diagnosis."
)


class LLMVisionProvider(BaseProvider):
    """Real vision via the configured LLM provider.

    INTEGRATION_READY: only meaningful when a non-mock LLM provider is active.
    Raises so the fallback chain proceeds to the local heuristic otherwise.
    """

    name = "llm_vision"
    status = MaturityStatus.INTEGRATION_READY
    requires_credentials = True

    def run(self, payload: BaseModel) -> Dict[str, Any]:
        assert isinstance(payload, VisionInput)
        client = get_llm_client()
        if client.is_mock:
            raise ProviderUnavailable("no real LLM provider active for vision")
        if settings.offline_first:
            raise ProviderUnavailable("offline/demo mode — real vision skipped")

        prompt = _PROMPT + (f"\nUser context: {payload.hint}" if payload.hint else "")
        try:
            resp = client.analyze_image(payload.image_bytes, prompt)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"llm vision call failed: {exc}") from exc

        data = _parse_json(resp.text)
        if not data:
            raise ProviderError("llm vision returned unparseable output")
        data.setdefault("method", f"llm vision ({client.name})")
        return VisionOutput.model_validate(data).model_dump()

    def health_check(self) -> HealthStatus:
        client = get_llm_client()
        if client.is_mock:
            return HealthStatus(
                component="provider:llm_vision",
                state=HealthState.WARNING,
                detail="no real LLM provider active (INTEGRATION_READY)",
                provider=self.name,
            )
        return HealthStatus(
            component="provider:llm_vision",
            state=HealthState.READY,
            detail=f"using LLM provider '{client.name}'",
            provider=self.name,
        )


def _parse_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{") :]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}

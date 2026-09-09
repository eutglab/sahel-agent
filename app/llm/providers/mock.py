"""Deterministic mock LLM.

MOCKED by design. It gives the agent a real *tool-calling loop* with zero cost
and zero network: it reads the ``AVAILABLE MODALITIES`` / ``AVAILABLE TOOLS``
hints in the prompt and asks for the relevant tools, then writes a templated
synthesis once tool results are supplied. This is honestly labelled everywhere
in the UI and docs as rule-based, not a language model.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from app.core.schemas import HealthState, HealthStatus, MaturityStatus
from app.llm.base import LLMClient, LLMResponse, ToolInvocation, ToolSpec


class MockLLMClient(LLMClient):
    name = "mock"
    status = MaturityStatus.MOCKED

    def complete(self, system: str, user: str, *, max_tokens: int = 800) -> LLMResponse:
        return LLMResponse(text=_templated_synthesis(user))

    def complete_with_tools(
        self,
        system: str,
        user: str,
        tools: List[ToolSpec],
        *,
        tool_results: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 900,
    ) -> LLMResponse:
        # Second turn: results are in, produce final text and stop.
        if tool_results:
            return LLMResponse(text=_templated_synthesis(user, tool_results), finish_reason="stop")

        modalities = _extract_list(user, "AVAILABLE MODALITIES")
        available = {t.name for t in tools}
        calls: List[ToolInvocation] = []

        if "image" in modalities and "analyze_image" in available:
            calls.append(ToolInvocation(name="analyze_image", arguments={"reason": "image supplied"}))
        if "sensors" in modalities and "analyze_sensor_data" in available:
            calls.append(ToolInvocation(name="analyze_sensor_data", arguments={"reason": "sensor readings supplied"}))
        if "location" in modalities and "get_weather" in available:
            calls.append(ToolInvocation(name="get_weather", arguments={"reason": "location supplied"}))

        # risk + recommendation always run last (the agent enforces ordering too).
        if "calculate_risk" in available:
            calls.append(ToolInvocation(name="calculate_risk", arguments={"reason": "combine evidence"}))
        if "generate_recommendation" in available:
            calls.append(ToolInvocation(name="generate_recommendation", arguments={"reason": "final synthesis"}))

        return LLMResponse(tool_calls=calls, finish_reason="tool_calls")

    def analyze_image(self, image_bytes: bytes, prompt: str) -> LLMResponse:
        payload = {
            "observations": [
                "Foliage visible; overall canopy structure discernible.",
                "Some colour variation across leaves (lighter patches in places).",
            ],
            "possible_signs": ["possible mild leaf discolouration"],
            "confidence": 0.4,
            "limitations": [
                "Single uncalibrated photo; no ground truth.",
                "Mock vision output — not a real model inference.",
            ],
        }
        return LLMResponse(text=json.dumps(payload))

    def health_check(self) -> HealthStatus:
        return HealthStatus(
            component="llm:mock",
            state=HealthState.READY,
            detail="deterministic mock — no cost, no network",
            provider=self.name,
        )


def _extract_list(text: str, label: str) -> List[str]:
    m = re.search(rf"{re.escape(label)}\s*:\s*([^\n]+)", text)
    if not m:
        return []
    return [item.strip().lower() for item in re.split(r"[,;]", m.group(1)) if item.strip()]


def _templated_synthesis(user: str, tool_results: Optional[List[Dict[str, Any]]] = None) -> str:
    level = "unknown"
    if tool_results:
        for res in tool_results:
            data = res.get("output") or {}
            combined = data.get("combined_risk")
            if isinstance(combined, dict):
                level = combined.get("level", level)
    return (
        "Based on the available multimodal evidence, the combined environmental risk "
        f"appears to be {level}. Sensor readings and (where present) image and weather "
        "signals were cross-checked; see the structured recommendation for prioritised "
        "actions. All figures are prototype indicators requiring field confirmation."
    )

"""Anthropic adapter — real reasoning + vision.

INTEGRATION_READY: active only when ``ANTHROPIC_API_KEY`` is set and the
``anthropic`` package is installed (kept out of requirements.txt so the demo
stays dependency-light). Any failure raises so the agent falls back to the
deterministic planner.
"""
from __future__ import annotations

import base64
import json
from typing import Any, Dict, List, Optional

from app.core.config import get_secret, settings
from app.core.errors import ProviderUnavailable
from app.core.schemas import HealthState, HealthStatus, MaturityStatus
from app.llm.base import LLMClient, LLMResponse, ToolInvocation, ToolSpec


class AnthropicLLMClient(LLMClient):
    name = "anthropic"
    status = MaturityStatus.INTEGRATION_READY

    def __init__(self) -> None:
        self._model = settings.anthropic_model
        self._key = get_secret("ANTHROPIC_API_KEY")

    def _client(self):
        if not self._key:
            raise ProviderUnavailable("ANTHROPIC_API_KEY not set")
        try:
            import anthropic
        except ImportError as exc:
            raise ProviderUnavailable("`pip install anthropic` to use this provider") from exc
        return anthropic.Anthropic(api_key=self._key)

    def complete(self, system: str, user: str, *, max_tokens: int = 800) -> LLMResponse:
        client = self._client()
        msg = client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")
        return LLMResponse(text=text, raw=msg, finish_reason=str(msg.stop_reason))

    def complete_with_tools(
        self,
        system: str,
        user: str,
        tools: List[ToolSpec],
        *,
        tool_results: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 900,
    ) -> LLMResponse:
        client = self._client()
        anthropic_tools = [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in tools
        ]
        content: List[Dict[str, Any]] = [{"type": "text", "text": user}]
        if tool_results:
            content.append(
                {"type": "text", "text": "TOOL RESULTS:\n" + json.dumps(tool_results, default=str)[:6000]}
            )
        msg = client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            tools=anthropic_tools or None,
            messages=[{"role": "user", "content": content}],
        )
        calls: List[ToolInvocation] = []
        text_parts: List[str] = []
        for block in msg.content:
            btype = getattr(block, "type", "")
            if btype == "tool_use":
                calls.append(ToolInvocation(name=block.name, arguments=dict(block.input or {})))
            elif btype == "text":
                text_parts.append(block.text)
        return LLMResponse(
            text="".join(text_parts),
            tool_calls=calls,
            raw=msg,
            finish_reason=str(msg.stop_reason),
        )

    def analyze_image(self, image_bytes: bytes, prompt: str) -> LLMResponse:
        client = self._client()
        b64 = base64.b64encode(image_bytes).decode()
        msg = client.messages.create(
            model=self._model,
            max_tokens=700,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        text = "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")
        return LLMResponse(text=text, raw=msg)

    def health_check(self) -> HealthStatus:
        if not self._key:
            return HealthStatus(
                component="llm:anthropic",
                state=HealthState.WARNING,
                detail="ANTHROPIC_API_KEY not set (INTEGRATION_READY)",
                provider=self.name,
            )
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return HealthStatus(
                component="llm:anthropic",
                state=HealthState.WARNING,
                detail="key set but `anthropic` package not installed",
                provider=self.name,
            )
        return HealthStatus(
            component="llm:anthropic",
            state=HealthState.READY,
            detail=f"key set, model {self._model}",
            provider=self.name,
        )

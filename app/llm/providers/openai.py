"""OpenAI adapter (alternative provider).

INTEGRATION_READY: active only when ``OPENAI_API_KEY`` is set and the ``openai``
package is installed. Also used as the shape for a generic OpenAI-compatible
"hackathon" endpoint (see hackathon.py).
"""
from __future__ import annotations

import base64
import json
from typing import Any, Dict, List, Optional

from app.core.config import get_secret, settings
from app.core.errors import ProviderUnavailable
from app.core.schemas import HealthState, HealthStatus, MaturityStatus
from app.llm.base import LLMClient, LLMResponse, ToolInvocation, ToolSpec


class OpenAILLMClient(LLMClient):
    name = "openai"
    status = MaturityStatus.INTEGRATION_READY

    def __init__(self, *, base_url: Optional[str] = None, api_key_env: str = "OPENAI_API_KEY",
                 model: Optional[str] = None, provider_name: Optional[str] = None) -> None:
        self._base_url = base_url
        self._key = get_secret(api_key_env)
        self._model = model or settings.openai_model
        if provider_name:
            self.name = provider_name

    def _client(self):
        if not self._key:
            raise ProviderUnavailable("API key not set for OpenAI-compatible provider")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderUnavailable("`pip install openai` to use this provider") from exc
        kwargs: Dict[str, Any] = {"api_key": self._key}
        if self._base_url:
            kwargs["base_url"] = self._base_url
        return OpenAI(**kwargs)

    def complete(self, system: str, user: str, *, max_tokens: int = 800) -> LLMResponse:
        client = self._client()
        resp = client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return LLMResponse(text=resp.choices[0].message.content or "", raw=resp)

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
        oa_tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema or {"type": "object", "properties": {}},
                },
            }
            for t in tools
        ]
        user_content = user
        if tool_results:
            user_content += "\n\nTOOL RESULTS:\n" + json.dumps(tool_results, default=str)[:6000]
        resp = client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            tools=oa_tools or None,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user_content}],
        )
        choice = resp.choices[0].message
        calls: List[ToolInvocation] = []
        for tc in getattr(choice, "tool_calls", None) or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            calls.append(ToolInvocation(name=tc.function.name, arguments=args))
        return LLMResponse(text=choice.content or "", tool_calls=calls, raw=resp)

    def analyze_image(self, image_bytes: bytes, prompt: str) -> LLMResponse:
        client = self._client()
        b64 = base64.b64encode(image_bytes).decode()
        resp = client.chat.completions.create(
            model=self._model,
            max_tokens=700,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    ],
                }
            ],
        )
        return LLMResponse(text=resp.choices[0].message.content or "", raw=resp)

    def health_check(self) -> HealthStatus:
        if not self._key:
            return HealthStatus(
                component=f"llm:{self.name}",
                state=HealthState.WARNING,
                detail="API key not set (INTEGRATION_READY)",
                provider=self.name,
            )
        return HealthStatus(
            component=f"llm:{self.name}",
            state=HealthState.READY,
            detail=f"key set, model {self._model}",
            provider=self.name,
        )

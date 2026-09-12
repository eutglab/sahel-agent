"""OpenAI adapter (alternative provider).

INTEGRATION_READY: active only when ``OPENAI_API_KEY`` is set and the ``openai``
package is installed. Also used as the shape for a generic OpenAI-compatible
"hackathon" endpoint (see hackathon.py) and for OpenRouter (see openrouter.py).
"""
from __future__ import annotations

import base64
import json
from typing import Any, Callable, Dict, List, Optional

from app.core.config import get_secret, settings
from app.core.errors import ProviderTimeout, ProviderUnavailable
from app.core.schemas import HealthState, HealthStatus, MaturityStatus
from app.llm.base import LLMClient, LLMResponse, ToolInvocation, ToolSpec


class OpenAILLMClient(LLMClient):
    name = "openai"
    status = MaturityStatus.INTEGRATION_READY

    def __init__(self, *, base_url: Optional[str] = None, api_key_env: str = "OPENAI_API_KEY",
                 model: Optional[str] = None, provider_name: Optional[str] = None,
                 timeout: Optional[float] = None) -> None:
        self._base_url = base_url
        self._key = get_secret(api_key_env)
        self._model = model or settings.openai_model
        self._timeout = timeout
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
        if self._timeout:
            kwargs["timeout"] = self._timeout
        return OpenAI(**kwargs)

    def _invoke(self, fn: Callable[..., Any], **kwargs: Any) -> Any:
        """Call an SDK method, translating any failure into a typed SahelError
        so the caller (agent / assistant) can fall back instead of crashing.
        Never leaks the API key: SDK exceptions carry status/message only."""
        try:
            return fn(**kwargs)
        except Exception as exc:  # noqa: BLE001 - classify below
            raise self._classify(exc) from exc

    def _classify(self, exc: Exception) -> Exception:
        try:
            import openai as openai_sdk
        except ImportError:
            return ProviderUnavailable(f"{self.name} request failed: {exc}")
        if isinstance(exc, getattr(openai_sdk, "APITimeoutError", ())):
            return ProviderTimeout(f"{self.name} timed out")
        if isinstance(exc, getattr(openai_sdk, "AuthenticationError", ())):
            return ProviderUnavailable(f"{self.name} authentication failed — check the API key")
        if isinstance(exc, getattr(openai_sdk, "RateLimitError", ())):
            return ProviderUnavailable(f"{self.name} rate limit or quota exceeded")
        if isinstance(exc, getattr(openai_sdk, "APIConnectionError", ())):
            return ProviderUnavailable(f"{self.name} network error: {exc}")
        status = getattr(exc, "status_code", None)
        if isinstance(exc, getattr(openai_sdk, "APIStatusError", ())) or status is not None:
            return ProviderUnavailable(f"{self.name} HTTP error" + (f" {status}" if status else ""))
        return ProviderUnavailable(f"{self.name} request failed: {exc}")

    @staticmethod
    def _require_choices(resp: Any, provider: str) -> Any:
        if not getattr(resp, "choices", None):
            raise ProviderUnavailable(f"{provider}: empty or malformed response (no choices)")
        return resp

    def complete(self, system: str, user: str, *, max_tokens: int = 800) -> LLMResponse:
        client = self._client()
        resp = self._require_choices(
            self._invoke(
                client.chat.completions.create,
                model=self._model,
                max_tokens=max_tokens,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            ),
            self.name,
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
        resp = self._require_choices(
            self._invoke(
                client.chat.completions.create,
                model=self._model,
                max_tokens=max_tokens,
                tools=oa_tools or None,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user_content}],
            ),
            self.name,
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
        # 1500, not a smaller "just enough for the JSON" budget: some models
        # (esp. free/reasoning-style ones on OpenRouter) spend a chunk of the
        # token budget on an internal reasoning pass before the JSON answer —
        # too tight a cap truncates the JSON mid-string (finish_reason
        # "length") and the vision provider then correctly rejects it as
        # unparseable, falling back to the local heuristic. Cheap to raise;
        # this call is only made when an elevated-effort vision read is worth it.
        resp = self._require_choices(
            self._invoke(
                client.chat.completions.create,
                model=self._model,
                max_tokens=1500,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                        ],
                    }
                ],
            ),
            self.name,
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

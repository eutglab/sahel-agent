from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel

from app.core.config import get_secret, settings
from app.core.errors import ProviderTimeout, ProviderUnavailable
from app.core.logging import get_logger
from app.core.schemas import HealthState, HealthStatus, MaturityStatus
from app.tools.base import BaseProvider
from app.tools.websearch.schema import WebSearchInput, WebSearchOutput

logger = get_logger("sahel.websearch")

_ENDPOINT = "https://api.exa.ai/search"


class ExaSearchProvider(BaseProvider):
    """Real web search via Exa (https://exa.ai) — neural search API.

    IMPLEMENTED. Skipped automatically in offline/demo mode or when no
    ``EXA_API_KEY`` is configured; any network error raises
    ``ProviderUnavailable`` so the fallback chain continues to the mock
    provider. Never fabricates results.
    """

    name = "exa"
    status = MaturityStatus.IMPLEMENTED
    requires_credentials = True

    def run(self, payload: BaseModel) -> Dict[str, Any]:
        assert isinstance(payload, WebSearchInput)
        if settings.offline_first:
            raise ProviderUnavailable("offline/demo mode — real web search skipped")

        api_key = get_secret("EXA_API_KEY") or get_secret("WEB_SEARCH_API_KEY")
        if not api_key:
            raise ProviderUnavailable("EXA_API_KEY not set")

        try:
            import requests
        except ImportError as exc:  # pragma: no cover
            raise ProviderUnavailable(f"requests not installed: {exc}") from exc

        body = {
            "query": payload.query,
            "numResults": payload.max_results,
            "type": "auto",
            "contents": {"text": {"maxCharacters": 400}},
        }
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        try:
            resp = requests.post(
                _ENDPOINT, json=body, headers=headers, timeout=settings.tool_timeout_seconds
            )
        except requests.Timeout as exc:
            raise ProviderTimeout(f"exa timed out after {settings.tool_timeout_seconds}s") from exc
        except requests.RequestException as exc:
            raise ProviderUnavailable(f"exa request failed: {exc}") from exc

        if resp.status_code != 200:
            raise ProviderUnavailable(f"exa HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        results = []
        for item in (data.get("results") or [])[: payload.max_results]:
            text = (item.get("text") or "").strip().replace("\n", " ")
            results.append(
                {
                    "title": item.get("title") or item.get("url", ""),
                    "url": item.get("url", ""),
                    "snippet": text[:280],
                    "published_date": item.get("publishedDate"),
                }
            )

        return WebSearchOutput(
            results=results,
            source="exa",
            query_used=payload.query,
            note="Live neural search results from Exa.",
        ).model_dump()

    def health_check(self) -> HealthStatus:
        api_key = get_secret("EXA_API_KEY") or get_secret("WEB_SEARCH_API_KEY")
        if not api_key:
            return HealthStatus(
                component="provider:exa",
                state=HealthState.WARNING,
                detail="EXA_API_KEY not set (INTEGRATION_READY)",
                provider=self.name,
            )
        return HealthStatus(
            component="provider:exa",
            state=HealthState.READY,
            detail="key set",
            provider=self.name,
        )

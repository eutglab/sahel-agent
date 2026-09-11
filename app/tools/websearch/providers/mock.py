from __future__ import annotations

import hashlib
from typing import Any, Dict

from pydantic import BaseModel

from app.core.schemas import MaturityStatus
from app.tools.base import BaseProvider
from app.tools.websearch.schema import WebSearchInput, WebSearchOutput


class MockWebSearchProvider(BaseProvider):
    """Deterministic offline stand-in for Exa — same query always yields the
    same sample results, clearly labelled as sample data.

    MOCKED by design: no network, no keys. Guarantees the "Evidence" section
    of the demo always renders something, even fully offline.
    """

    name = "mock"
    status = MaturityStatus.MOCKED

    def run(self, payload: BaseModel) -> Dict[str, Any]:
        assert isinstance(payload, WebSearchInput)
        seed = int(hashlib.sha256(payload.query.encode()).hexdigest(), 16)
        topics = [
            "Smallholder irrigation scheduling under heat stress",
            "Regional agronomic advisory — dry-season crop management",
            "Field guide: recognising early water-stress symptoms",
        ]
        results = []
        for i in range(min(payload.max_results, 3)):
            results.append(
                {
                    "title": f"[sample] {topics[(seed + i) % len(topics)]}",
                    "url": f"https://example.org/advisory/{(seed + i) % 999}",
                    "snippet": (
                        "Sample offline reference generated for demonstration — no live "
                        "network call was made. Configure EXA_API_KEY for real, cited sources."
                    ),
                    "published_date": None,
                }
            )
        return WebSearchOutput(
            results=results,
            source="sample (offline)",
            query_used=payload.query,
            note="Offline sample data — not real search results. Set EXA_API_KEY to go live.",
        ).model_dump()

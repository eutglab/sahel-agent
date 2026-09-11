from __future__ import annotations

from typing import Dict, List, Type

from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger
from app.core.schemas import MaturityStatus
from app.tools.base import BaseProvider, BaseTool
from app.tools.websearch.providers.exa import ExaSearchProvider
from app.tools.websearch.providers.mock import MockWebSearchProvider
from app.tools.websearch.schema import WebSearchInput, WebSearchOutput

logger = get_logger("sahel.websearch")

_PROVIDERS: Dict[str, type[BaseProvider]] = {
    "exa": ExaSearchProvider,
    "mock": MockWebSearchProvider,
}


class WebSearchTool(BaseTool):
    name = "search_web"
    description = (
        "Search the live web for evidence relevant to a detected environmental risk "
        "(advisories, guidance, recent reports). Real provider is Exa; falls back to "
        "clearly-labelled sample data offline. Only called when the agent has "
        "something specific to ground — never a generic lookup."
    )
    status = MaturityStatus.IMPLEMENTED

    def input_schema(self) -> Type[BaseModel]:
        return WebSearchInput

    def output_schema(self) -> Type[BaseModel]:
        return WebSearchOutput


def _resolve_chain() -> List[BaseProvider]:
    names: List[str] = []
    primary = settings.web_search_provider
    if primary in _PROVIDERS:
        names.append(primary)
    for name in settings.web_search_fallback_chain:
        if name in _PROVIDERS and name not in names:
            names.append(name)
    if "mock" not in names:
        names.append("mock")  # guarantee a terminal provider
    return [_PROVIDERS[n]() for n in names]


def build() -> WebSearchTool:
    return WebSearchTool(providers=_resolve_chain())

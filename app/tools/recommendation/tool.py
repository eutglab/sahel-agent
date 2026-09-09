from __future__ import annotations

from typing import Dict, List, Type

from pydantic import BaseModel

from app.core.config import settings
from app.core.schemas import MaturityStatus
from app.tools.base import BaseProvider, BaseTool
from app.tools.recommendation.providers.hackathon import HackathonRecommendationProvider
from app.tools.recommendation.providers.llm import LLMRecommendationProvider
from app.tools.recommendation.providers.template import TemplateRecommendationProvider
from app.tools.recommendation.schema import RecommendationInput, RecommendationOutput

_PROVIDERS: Dict[str, type[BaseProvider]] = {
    "template": TemplateRecommendationProvider,
    "llm": LLMRecommendationProvider,
    "hackathon": HackathonRecommendationProvider,
}


class RecommendationTool(BaseTool):
    name = "generate_recommendation"
    description = (
        "Turn the combined sensor/image/weather/risk evidence into a prioritised, "
        "actionable recommendation with monitoring steps, warnings, confidence and "
        "limitations. Deterministic by default; optional LLM synthesis grounded on "
        "the structured inputs."
    )
    status = MaturityStatus.IMPLEMENTED

    def input_schema(self) -> Type[BaseModel]:
        return RecommendationInput

    def output_schema(self) -> Type[BaseModel]:
        return RecommendationOutput


def _resolve_chain() -> List[BaseProvider]:
    names: List[str] = []
    if settings.recommendation_provider in _PROVIDERS:
        names.append(settings.recommendation_provider)
    for name in settings.recommendation_fallback_chain:
        if name in _PROVIDERS and name not in names:
            names.append(name)
    if "template" not in names:
        names.append("template")  # guaranteed terminal provider
    return [_PROVIDERS[n]() for n in names]


def build() -> RecommendationTool:
    return RecommendationTool(providers=_resolve_chain())

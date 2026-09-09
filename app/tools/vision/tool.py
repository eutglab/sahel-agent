from __future__ import annotations

from typing import Any, Dict, List, Type

from pydantic import BaseModel

from app.core.config import settings
from app.core.errors import ToolInputError
from app.core.schemas import MaturityStatus
from app.core.security import validate_image_upload
from app.tools.base import BaseProvider, BaseTool
from app.tools.vision.providers.hackathon import HackathonVisionProvider
from app.tools.vision.providers.llm_vision import LLMVisionProvider
from app.tools.vision.providers.local_heuristic import LocalHeuristicVisionProvider
from app.tools.vision.providers.mock import MockVisionProvider
from app.tools.vision.schema import VisionInput, VisionOutput

_PROVIDERS: Dict[str, type[BaseProvider]] = {
    "llm_vision": LLMVisionProvider,
    "local_heuristic": LocalHeuristicVisionProvider,
    "mock": MockVisionProvider,
    "hackathon": HackathonVisionProvider,
}


class VisionAnalysisTool(BaseTool):
    name = "analyze_image"
    description = (
        "Analyse a plant/field photo and return cautious visual observations and "
        "possible stress signs with a confidence score and explicit limitations. "
        "Never returns a definitive diagnosis."
    )
    status = MaturityStatus.IMPLEMENTED

    def input_schema(self) -> Type[BaseModel]:
        return VisionInput

    def output_schema(self) -> Type[BaseModel]:
        return VisionOutput

    def validate_input(self, raw: Any) -> BaseModel:
        payload = super().validate_input(raw)
        # An invalid/corrupt image is a hard input error: the agent should
        # continue WITHOUT a visual observation, not fall through to mock data.
        try:
            validate_image_upload(payload.image_bytes)  # type: ignore[attr-defined]
        except ToolInputError:
            raise
        return payload


def _resolve_chain() -> List[BaseProvider]:
    names: List[str] = []
    if settings.vision_provider in _PROVIDERS:
        names.append(settings.vision_provider)
    for name in settings.vision_fallback_chain:
        if name in _PROVIDERS and name not in names:
            names.append(name)
    for guaranteed in ("local_heuristic", "mock"):
        if guaranteed not in names:
            names.append(guaranteed)
    return [_PROVIDERS[n]() for n in names]


def build() -> VisionAnalysisTool:
    return VisionAnalysisTool(providers=_resolve_chain())

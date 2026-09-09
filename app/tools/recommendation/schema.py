from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class RecommendationInput(BaseModel):
    sensors: Dict[str, Any] | None = None
    vision: Dict[str, Any] | None = None
    weather: Dict[str, Any] | None = None
    risk: Dict[str, Any] | None = None
    growth_stage: str = "unknown"
    modalities: List[str] = Field(default_factory=list)


class RecommendationOutput(BaseModel):
    priority: str                       # low | medium | high
    main_finding: str
    recommended_actions: List[str] = Field(default_factory=list)
    monitoring_actions: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    limitations: List[str] = Field(default_factory=list)
    method: str = "deterministic template"

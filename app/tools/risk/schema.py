from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class RiskInput(BaseModel):
    """Merged evidence from earlier tools. All parts optional — the calculator
    works with whatever is available and reports reduced confidence."""
    sensors: Dict[str, Any] | None = None
    vision: Dict[str, Any] | None = None
    weather: Dict[str, Any] | None = None
    growth_stage: str = "unknown"


class SubScore(BaseModel):
    name: str
    score: float = Field(ge=0, le=1)
    level: str            # low | moderate | high
    drivers: List[str] = Field(default_factory=list)


class CrossCheck(BaseModel):
    converging_evidence: List[str] = Field(default_factory=list)
    diverging_evidence: List[str] = Field(default_factory=list)
    confidence_adjustment: float = 0.0


class RiskOutput(BaseModel):
    water_stress: SubScore
    heat_stress: SubScore
    environmental: SubScore
    combined_risk: SubScore
    cross_check: CrossCheck
    confidence: float = Field(ge=0, le=1)
    disclaimer: str = (
        "Prototype indicator derived from transparent heuristics. Not a validated "
        "agronomic model. Requires local calibration and field confirmation."
    )

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from app.core.schemas import GrowthStage


class SensorInput(BaseModel):
    temperature_c: float | None = None
    soil_moisture_pct: float | None = Field(default=None, ge=0, le=100)
    air_humidity_pct: float | None = Field(default=None, ge=0, le=100)
    rainfall_mm: float | None = Field(default=None, ge=0)
    growth_stage: GrowthStage = GrowthStage.unknown


class SensorIndicator(BaseModel):
    name: str
    value: float | None
    assessment: str          # e.g. "critically low", "optimal", "elevated"
    detail: str = ""


class SensorOutput(BaseModel):
    risk_level: str           # low | moderate | elevated | high
    indicators: List[SensorIndicator] = Field(default_factory=list)
    anomalies: List[str] = Field(default_factory=list)
    explanation: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    method: str = "rule-based thresholds (prototype, requires local calibration)"

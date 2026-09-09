"""Cross-cutting Pydantic contracts shared by the agent and every tool.

Tool-specific input/output models live in ``app/tools/<name>/schema.py``.
"""
from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Honesty taxonomy — attached to every tool and provider.
# --------------------------------------------------------------------------- #
class MaturityStatus(str, Enum):
    IMPLEMENTED = "IMPLEMENTED"          # real code, works offline, tested
    MOCKED = "MOCKED"                    # real interface, synthetic data by design
    INTEGRATION_READY = "INTEGRATION_READY"  # contract + adapter slot, not wired live
    FUTURE = "FUTURE"                    # documented only, no implementation


class HealthState(str, Enum):
    READY = "READY"
    WARNING = "WARNING"
    FAILED = "FAILED"


class HealthStatus(BaseModel):
    component: str
    state: HealthState
    detail: str = ""
    provider: Optional[str] = None


# --------------------------------------------------------------------------- #
# Agent input — the raw multimodal context supplied by the UI or a scenario.
# --------------------------------------------------------------------------- #
class GrowthStage(str, Enum):
    germination = "germination"
    vegetative = "vegetative"
    flowering = "flowering"
    fruiting = "fruiting"
    maturity = "maturity"
    unknown = "unknown"


class SensorReadings(BaseModel):
    temperature_c: Optional[float] = Field(default=None, description="Air temperature, °C")
    soil_moisture_pct: Optional[float] = Field(default=None, ge=0, le=100)
    air_humidity_pct: Optional[float] = Field(default=None, ge=0, le=100)
    rainfall_mm: Optional[float] = Field(default=None, ge=0)
    growth_stage: GrowthStage = GrowthStage.unknown

    def present_fields(self) -> List[str]:
        names = []
        for key in ("temperature_c", "soil_moisture_pct", "air_humidity_pct", "rainfall_mm"):
            if getattr(self, key) is not None:
                names.append(key)
        if self.growth_stage != GrowthStage.unknown:
            names.append("growth_stage")
        return names


class Location(BaseModel):
    label: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)

    @property
    def has_coordinates(self) -> bool:
        return self.latitude is not None and self.longitude is not None


class AgentInput(BaseModel):
    """Everything the agent is given for one analysis."""
    text_context: str = ""
    image_bytes: Optional[bytes] = Field(default=None, repr=False, exclude=True)
    image_name: Optional[str] = None
    sensors: SensorReadings = Field(default_factory=SensorReadings)
    location: Location = Field(default_factory=Location)
    scenario_id: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True}

    def available_modalities(self) -> List[str]:
        mods: List[str] = []
        if self.image_bytes:
            mods.append("image")
        if self.sensors.present_fields():
            mods.append("sensors")
        if self.location.label or self.location.has_coordinates:
            mods.append("location")
        if self.text_context.strip():
            mods.append("text")
        return mods


# --------------------------------------------------------------------------- #
# Tool call records + agent trace.
# --------------------------------------------------------------------------- #
class ToolCallRecord(BaseModel):
    tool_name: str
    provider_used: Optional[str] = None
    source_note: str = ""            # e.g. "real API timed out -> local dataset"
    input_summary: Dict[str, Any] = Field(default_factory=dict)
    started_at: float = Field(default_factory=time.time)
    completed_at: Optional[float] = None
    success: bool = False
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @property
    def duration_ms(self) -> float:
        if self.completed_at is None:
            return 0.0
        return round((self.completed_at - self.started_at) * 1000, 1)


class TraceEvent(BaseModel):
    label: str
    status: str = "info"            # info | ok | warn | error
    detail: str = ""
    at: float = Field(default_factory=time.time)


class AgentTrace(BaseModel):
    events: List[TraceEvent] = Field(default_factory=list)
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)

    def event(self, label: str, status: str = "info", detail: str = "") -> None:
        self.events.append(TraceEvent(label=label, status=status, detail=detail))

    def as_lines(self) -> List[str]:
        icon = {"info": "•", "ok": "✓", "warn": "!", "error": "✗"}
        return [f"{icon.get(e.status, '•')} {e.label}" + (f" — {e.detail}" if e.detail else "") for e in self.events]


# --------------------------------------------------------------------------- #
# Fused multimodal observation + final agent result.
# --------------------------------------------------------------------------- #
class ObservationBundle(BaseModel):
    """Merged view of every tool output — the input to risk + recommendation."""
    modalities: List[str] = Field(default_factory=list)
    vision: Optional[Dict[str, Any]] = None
    sensors: Optional[Dict[str, Any]] = None
    weather: Optional[Dict[str, Any]] = None
    risk: Optional[Dict[str, Any]] = None
    notes: List[str] = Field(default_factory=list)


class AgentResult(BaseModel):
    scenario_id: Optional[str] = None
    reasoning_mode: str = "deterministic"   # llm_tool_calling | deterministic | precomputed
    modalities_used: List[str] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    observation: ObservationBundle = Field(default_factory=ObservationBundle)
    recommendation: Optional[Dict[str, Any]] = None
    trace: AgentTrace = Field(default_factory=AgentTrace)
    execution_ms: float = 0.0
    degraded: bool = False                  # True if a fallback level was needed
    errors: List[str] = Field(default_factory=list)

    def situation_line(self) -> str:
        risk = (self.observation.risk or {}).get("combined_risk", {})
        level = risk.get("level", "unknown")
        return f"Overall environmental risk: {level.upper()}"

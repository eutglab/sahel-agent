from __future__ import annotations

from typing import Any, Dict, Type

from pydantic import BaseModel

from app.core.schemas import HealthState, HealthStatus, MaturityStatus
from app.tools.base import BaseProvider, BaseTool
from app.tools.sensors.rules import analyze
from app.tools.sensors.schema import SensorInput, SensorOutput


class RuleSensorProvider(BaseProvider):
    name = "rules"
    status = MaturityStatus.IMPLEMENTED

    def run(self, payload: BaseModel) -> Dict[str, Any]:
        assert isinstance(payload, SensorInput)
        return analyze(payload)

    def health_check(self) -> HealthStatus:
        return HealthStatus(
            component="provider:rules",
            state=HealthState.READY,
            detail="deterministic threshold engine (thresholds.yaml)",
            provider=self.name,
        )


class SensorAnalysisTool(BaseTool):
    name = "analyze_sensor_data"
    description = (
        "Evaluate environmental sensor readings (temperature, soil moisture, air "
        "humidity, rainfall, growth stage) against configurable prototype thresholds "
        "and return risk level, anomalies and a plain-language explanation."
    )
    status = MaturityStatus.IMPLEMENTED

    def input_schema(self) -> Type[BaseModel]:
        return SensorInput

    def output_schema(self) -> Type[BaseModel]:
        return SensorOutput


def build() -> SensorAnalysisTool:
    return SensorAnalysisTool(providers=[RuleSensorProvider()])

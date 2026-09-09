from __future__ import annotations

from typing import Any, Dict, Type

from pydantic import BaseModel

from app.core.schemas import HealthState, HealthStatus, MaturityStatus
from app.tools.base import BaseProvider, BaseTool
from app.tools.risk.rules import calculate
from app.tools.risk.schema import RiskInput, RiskOutput


class RuleRiskProvider(BaseProvider):
    name = "heuristic"
    status = MaturityStatus.IMPLEMENTED

    def run(self, payload: BaseModel) -> Dict[str, Any]:
        assert isinstance(payload, RiskInput)
        return calculate(payload)

    def health_check(self) -> HealthStatus:
        return HealthStatus(
            component="provider:heuristic",
            state=HealthState.READY,
            detail="transparent weighted scoring (prototype)",
            provider=self.name,
        )


class RiskCalculatorTool(BaseTool):
    name = "calculate_risk"
    description = (
        "Combine sensor, image and weather evidence into explainable prototype "
        "risk indicators: water stress, heat stress, environmental, and a weighted "
        "combined score. Includes a cross-check of converging/diverging evidence."
    )
    status = MaturityStatus.IMPLEMENTED

    def input_schema(self) -> Type[BaseModel]:
        return RiskInput

    def output_schema(self) -> Type[BaseModel]:
        return RiskOutput


def build() -> RiskCalculatorTool:
    return RiskCalculatorTool(providers=[RuleRiskProvider()])

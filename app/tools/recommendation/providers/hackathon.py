from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel

from app.core.errors import NotIntegratedError
from app.core.schemas import HealthState, HealthStatus, MaturityStatus
from app.tools.base import BaseProvider
from app.tools.recommendation.schema import RecommendationInput


class HackathonRecommendationProvider(BaseProvider):
    """Placeholder for an organiser-provided recommendation/agronomy service."""

    name = "hackathon"
    status = MaturityStatus.INTEGRATION_READY
    requires_credentials = True

    def run(self, payload: BaseModel) -> Dict[str, Any]:
        assert isinstance(payload, RecommendationInput)
        raise NotIntegratedError(
            "hackathon recommendation provider not implemented — "
            "fill app/tools/recommendation/providers/hackathon.py"
        )

    def health_check(self) -> HealthStatus:
        return HealthStatus(
            component="provider:hackathon",
            state=HealthState.WARNING,
            detail="not implemented (INTEGRATION_READY)",
            provider=self.name,
        )

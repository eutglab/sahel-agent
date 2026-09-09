from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel

from app.core.errors import NotIntegratedError
from app.core.schemas import HealthState, HealthStatus, MaturityStatus
from app.tools.base import BaseProvider
from app.tools.vision.schema import VisionInput

# ---------------------------------------------------------------------------
# HACKATHON VISION PROVIDER — skeleton.
# On the day: implement `run()` against the organiser-provided vision API and
# map its response to VisionOutput. Then add `hackathon` to VISION_FALLBACK_CHAIN
# or set VISION_PROVIDER=hackathon.
# ---------------------------------------------------------------------------


class HackathonVisionProvider(BaseProvider):
    name = "hackathon"
    status = MaturityStatus.INTEGRATION_READY
    requires_credentials = True

    def run(self, payload: BaseModel) -> Dict[str, Any]:
        assert isinstance(payload, VisionInput)
        raise NotIntegratedError(
            "hackathon vision provider not implemented — fill app/tools/vision/providers/hackathon.py"
        )

    def health_check(self) -> HealthStatus:
        return HealthStatus(
            component="provider:hackathon",
            state=HealthState.WARNING,
            detail="not implemented (INTEGRATION_READY)",
            provider=self.name,
        )

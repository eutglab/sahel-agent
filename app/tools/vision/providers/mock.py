from __future__ import annotations

import hashlib
from typing import Any, Dict

from pydantic import BaseModel

from app.core.schemas import MaturityStatus
from app.tools.base import BaseProvider
from app.tools.vision.schema import VisionInput, VisionOutput


class MockVisionProvider(BaseProvider):
    """Deterministic placeholder observations. MOCKED — terminal fallback."""

    name = "mock"
    status = MaturityStatus.MOCKED

    def run(self, payload: BaseModel) -> Dict[str, Any]:
        assert isinstance(payload, VisionInput)
        h = int(hashlib.sha256(payload.image_bytes[:2048] or b"x").hexdigest(), 16)
        variants = [
            (["Canopy visible, mostly green.", "Minor colour variation on some leaves."],
             ["possible mild leaf-margin discolouration"]),
            (["Dense foliage, uniform colour.", "No obvious large lesions in frame."],
             []),
            (["Mixed light and shade across the canopy.", "A few lighter patches visible."],
             ["possible early senescence or light stress"]),
        ]
        obs, signs = variants[h % len(variants)]
        return VisionOutput(
            observations=obs,
            possible_signs=signs,
            confidence=0.3,
            limitations=[
                "Mock vision output — not a real model inference.",
                "For demonstration of the agent pipeline only.",
            ],
            method="mock",
        ).model_dump()

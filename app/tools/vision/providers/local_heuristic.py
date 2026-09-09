"""Local, offline image heuristic — colour statistics only, no ML model.

IMPLEMENTED. Computes the fraction of green / yellow-brown / dark pixels and the
mean brightness, then reports *cautious* possible signs. This is deliberately
simple and is documented as a prototype heuristic, not plant pathology.
"""
from __future__ import annotations

from typing import Any, Dict

import numpy as np
from pydantic import BaseModel

from app.core.errors import ProviderError
from app.core.schemas import MaturityStatus
from app.core.security import load_image_safe
from app.tools.base import BaseProvider
from app.tools.vision.schema import VisionInput, VisionOutput


class LocalHeuristicVisionProvider(BaseProvider):
    name = "local_heuristic"
    status = MaturityStatus.IMPLEMENTED

    def run(self, payload: BaseModel) -> Dict[str, Any]:
        assert isinstance(payload, VisionInput)
        try:
            img = load_image_safe(payload.image_bytes)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"image could not be analysed: {exc}") from exc

        arr = np.asarray(img.resize((160, 160))).astype(np.float32)
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
        total = arr.shape[0] * arr.shape[1]

        brightness = float(arr.mean() / 255.0)
        green_mask = (g > r + 12) & (g > b + 12)
        yellow_brown_mask = (r > 90) & (g > 70) & (b < 90) & (np.abs(r - g) < 60) & ~green_mask
        dark_mask = arr.mean(axis=-1) < 55

        green_frac = float(green_mask.sum() / total)
        yb_frac = float(yellow_brown_mask.sum() / total)
        dark_frac = float(dark_mask.sum() / total)

        observations = [
            f"Green foliage covers ~{green_frac * 100:.0f}% of the frame.",
            f"Yellow/brown tones cover ~{yb_frac * 100:.0f}% of the frame.",
            f"Mean brightness ~{brightness * 100:.0f}% of maximum.",
        ]
        possible_signs = []
        if yb_frac > 0.18 and yb_frac > green_frac * 0.5:
            possible_signs.append("noticeable yellow/brown discolouration — potential stress or senescence")
        if green_frac < 0.15:
            possible_signs.append("low green cover — possible sparse canopy or off-target framing")
        if dark_frac > 0.35:
            possible_signs.append("large dark regions — possible shadow, necrosis, or exposure issue")
        if brightness < 0.25:
            possible_signs.append("image is dark — lighting may limit reliability")

        confidence = 0.35 + min(0.25, yb_frac + (0.1 if green_frac > 0.2 else 0))
        confidence = round(min(confidence, 0.6), 2)

        return VisionOutput(
            observations=observations,
            possible_signs=possible_signs,
            confidence=confidence,
            limitations=[
                "Colour-statistics heuristic only — not plant pathology.",
                "Sensitive to lighting, camera, background and framing.",
                "Possible signs require field confirmation by a qualified person.",
            ],
            method="local colour heuristic",
        ).model_dump()

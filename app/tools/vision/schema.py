from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class VisionInput(BaseModel):
    image_bytes: bytes = Field(repr=False)
    hint: str = ""          # optional free-text context from the user

    model_config = {"arbitrary_types_allowed": True}


class VisionOutput(BaseModel):
    observations: List[str] = Field(default_factory=list)
    possible_signs: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1, default=0.0)
    limitations: List[str] = Field(default_factory=list)
    method: str = ""        # "local colour heuristic" | "llm vision" | "mock"

    def model_post_init(self, __context) -> None:  # noqa: D401
        if not self.limitations:
            self.limitations = [
                "Not a diagnosis. Possible signs only; requires field confirmation.",
            ]

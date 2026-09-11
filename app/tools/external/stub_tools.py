"""INTEGRATION_READY / FUTURE tool interfaces.

These declare the contract for capabilities we have NOT wired to a real service.
They are registered *disabled by default* (see .env.example) and their
``execute`` raises ``NotIntegratedError`` — the agent never fabricates data for
them. On hackathon day, either implement the provider or use
``register_external_tool`` from app.tools.external.adapter.

Note: ``search_web`` graduated to a real IMPLEMENTED tool backed by Exa — see
``app.tools.websearch``.
"""
from __future__ import annotations

from typing import Any, Dict, Type

from pydantic import BaseModel, Field

from app.core.errors import NotIntegratedError
from app.core.schemas import HealthState, HealthStatus, MaturityStatus
from app.tools.base import BaseProvider, BaseTool


class _NotIntegratedProvider(BaseProvider):
    def __init__(self, capability: str) -> None:
        self.name = "not_integrated"
        self.status = MaturityStatus.INTEGRATION_READY
        self._capability = capability

    def run(self, payload: BaseModel) -> Dict[str, Any]:
        raise NotIntegratedError(
            f"'{self._capability}' is INTEGRATION_READY but not connected. "
            f"Implement a provider or use register_external_tool()."
        )

    def health_check(self) -> HealthStatus:
        return HealthStatus(
            component=f"provider:{self._capability}",
            state=HealthState.WARNING,
            detail="INTEGRATION_READY — not connected",
            provider=self.name,
        )


# --- file analysis ------------------------------------------------------ #
class FileAnalysisInput(BaseModel):
    filename: str
    content_b64: str = ""


class FileAnalysisOutput(BaseModel):
    summary: str = ""
    fields: dict = Field(default_factory=dict)


class FileAnalysisTool(BaseTool):
    name = "analyze_file"
    description = "Extract structured data from an uploaded document (CSV/PDF/etc.) (INTEGRATION_READY)."
    status = MaturityStatus.INTEGRATION_READY

    def input_schema(self) -> Type[BaseModel]:
        return FileAnalysisInput

    def output_schema(self) -> Type[BaseModel]:
        return FileAnalysisOutput


def build_file_analysis() -> FileAnalysisTool:
    return FileAnalysisTool(providers=[_NotIntegratedProvider("file_analysis")])


# --- notification ----------------------------------------------------- #
class NotificationInput(BaseModel):
    message: str
    channel: str = "log"


class NotificationOutput(BaseModel):
    delivered: bool = False
    channel: str = ""


class NotificationTool(BaseTool):
    name = "send_notification"
    description = "Send an alert to an external channel (SMS/e-mail/webhook) (INTEGRATION_READY)."
    status = MaturityStatus.INTEGRATION_READY

    def input_schema(self) -> Type[BaseModel]:
        return NotificationInput

    def output_schema(self) -> Type[BaseModel]:
        return NotificationOutput


def build_notification() -> NotificationTool:
    return NotificationTool(providers=[_NotIntegratedProvider("notification")])

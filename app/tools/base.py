"""The single contract every tool obeys, plus the provider + fallback machinery.

    Agent -> Tool -> Provider interface -> Provider adapter -> External service

The agent only ever talks to ``BaseTool``. A tool delegates the actual work to
an ordered *fallback chain* of providers and records which one produced the
result (surfaced in the trace as ``source_note``).
"""
from __future__ import annotations

import abc
import time
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ValidationError

from app.core.errors import (
    NotIntegratedError,
    ProviderError,
    ToolInputError,
    ToolOutputError,
)
from app.core.logging import get_logger
from app.core.schemas import HealthState, HealthStatus, MaturityStatus, ToolCallRecord

logger = get_logger("sahel.tools")


class ToolMetadata(BaseModel):
    name: str
    description: str
    version: str = "0.1.0"
    status: MaturityStatus = MaturityStatus.IMPLEMENTED
    provider_active: Optional[str] = None
    fallback_chain: List[str] = []
    requires_credentials: bool = False
    enabled: bool = True


class BaseProvider(abc.ABC):
    """A concrete adapter behind a tool (mock / local / real / hackathon)."""

    name: str = "base"
    status: MaturityStatus = MaturityStatus.IMPLEMENTED
    requires_credentials: bool = False

    @abc.abstractmethod
    def run(self, payload: BaseModel) -> Dict[str, Any]:
        """Execute and return a plain dict matching the tool's output schema."""

    def health_check(self) -> HealthStatus:
        return HealthStatus(
            component=f"provider:{self.name}",
            state=HealthState.READY,
            detail="static provider",
            provider=self.name,
        )


class BaseTool(abc.ABC):
    """Common contract — see module docstring."""

    name: str = "base"
    description: str = ""
    version: str = "0.1.0"
    status: MaturityStatus = MaturityStatus.IMPLEMENTED
    requires_credentials: bool = False

    #: Ordered provider instances. First that succeeds wins.
    def __init__(self, providers: Optional[List[BaseProvider]] = None) -> None:
        self._providers: List[BaseProvider] = providers or []

    # --- schema hooks ---------------------------------------------------- #
    @abc.abstractmethod
    def input_schema(self) -> Type[BaseModel]:
        ...

    @abc.abstractmethod
    def output_schema(self) -> Type[BaseModel]:
        ...

    # --- lifecycle ----------------------------------------------------- #
    def providers(self) -> List[BaseProvider]:
        return list(self._providers)

    def set_providers(self, providers: List[BaseProvider]) -> None:
        self._providers = providers

    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=self.name,
            description=self.description,
            version=self.version,
            status=self.status,
            provider_active=self._providers[0].name if self._providers else None,
            fallback_chain=[p.name for p in self._providers],
            requires_credentials=self.requires_credentials,
        )

    def validate_input(self, raw: Any) -> BaseModel:
        schema = self.input_schema()
        if isinstance(raw, schema):
            return raw
        try:
            return schema.model_validate(raw)
        except ValidationError as exc:
            raise ToolInputError(f"{self.name}: invalid input — {exc.errors()[:2]}") from exc

    def validate_output(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        schema = self.output_schema()
        try:
            return schema.model_validate(raw).model_dump()
        except ValidationError as exc:
            raise ToolOutputError(f"{self.name}: provider output rejected — {exc.errors()[:2]}") from exc

    # --- execution --------------------------------------------------- #
    def execute(self, raw_input: Any) -> ToolCallRecord:
        """Run the fallback chain; always returns a ToolCallRecord (never raises
        for provider failures — those are captured on the record)."""
        record = ToolCallRecord(tool_name=self.name)
        try:
            payload = self.validate_input(raw_input)
        except ToolInputError as exc:
            record.completed_at = time.time()
            record.error = str(exc)
            return record

        record.input_summary = _summarize(payload)

        if not self._providers:
            record.completed_at = time.time()
            record.error = f"{self.name}: no providers configured"
            return record

        attempted: List[str] = []
        last_err: Optional[str] = None
        for provider in self._providers:
            attempted.append(provider.name)
            try:
                raw_out = provider.run(payload)
                validated = self.validate_output(raw_out)
            except NotIntegratedError as exc:
                last_err = f"{provider.name}: not integrated ({exc})"
                logger.info("%s provider %s not integrated", self.name, provider.name)
                continue
            except (ProviderError, ToolOutputError) as exc:
                last_err = f"{provider.name}: {exc}"
                logger.warning("%s provider %s failed: %s", self.name, provider.name, exc)
                continue
            except Exception as exc:  # noqa: BLE001 - defensive: keep the agent alive
                last_err = f"{provider.name}: unexpected {type(exc).__name__}: {exc}"
                logger.warning("%s provider %s crashed: %s", self.name, provider.name, exc)
                continue

            record.provider_used = provider.name
            record.output = validated
            record.success = True
            record.completed_at = time.time()
            if attempted[:-1]:
                record.source_note = (
                    f"used '{provider.name}' after {', '.join(attempted[:-1])} failed"
                )
            else:
                record.source_note = f"used '{provider.name}'"
            return record

        record.completed_at = time.time()
        record.error = f"all providers failed ({' -> '.join(attempted)}): {last_err}"
        return record

    # --- health ---------------------------------------------------- #
    def health_check(self) -> HealthStatus:
        if not self._providers:
            return HealthStatus(
                component=f"tool:{self.name}",
                state=HealthState.FAILED,
                detail="no providers configured",
            )
        states = [p.health_check() for p in self._providers]
        if any(s.state == HealthState.READY for s in states):
            worst = HealthState.READY
        elif any(s.state == HealthState.WARNING for s in states):
            worst = HealthState.WARNING
        else:
            worst = HealthState.FAILED
        detail = "; ".join(f"{s.provider}:{s.state.value}" for s in states)
        return HealthStatus(
            component=f"tool:{self.name}",
            state=worst,
            detail=detail,
            provider=self._providers[0].name,
        )


def _summarize(model: BaseModel) -> Dict[str, Any]:
    """Compact, log-safe view of a tool input (drops bytes / long strings)."""
    out: Dict[str, Any] = {}
    for key, value in model.model_dump().items():
        if isinstance(value, (bytes, bytearray)):
            out[key] = f"<{len(value)} bytes>"
        elif isinstance(value, str) and len(value) > 120:
            out[key] = value[:120] + "…"
        else:
            out[key] = value
    return out

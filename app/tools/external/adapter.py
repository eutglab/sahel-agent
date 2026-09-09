"""Turn any callable into a registry-visible tool — the hackathon fast path.

Example (hackathon day)::

    from app.tools.external.adapter import register_external_tool

    def search(payload: dict) -> dict:
        # call the organiser's API...
        return {"results": [...], "source": "acme-search"}

    register_external_tool(
        name="hackathon_search",
        description="Search external environmental knowledge",
        handler=search,
        input_fields={"query": (str, ...)},
        output_fields={"results": (list, ...), "source": (str, "")},
    )

The agent then discovers ``hackathon_search`` automatically via
``registry.describe_for_llm()`` and can call it in the loop.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple, Type

from pydantic import BaseModel, ConfigDict, create_model

from app.core.errors import ProviderError
from app.core.schemas import HealthState, HealthStatus, MaturityStatus
from app.tools.base import BaseProvider, BaseTool
from app.tools.registry import get_registry

Handler = Callable[[Dict[str, Any]], Dict[str, Any]]


def _model_from_fields(name: str, fields: Optional[Dict[str, Tuple[type, Any]]]) -> Type[BaseModel]:
    if not fields:
        return create_model(name, __config__=ConfigDict(extra="allow"))
    return create_model(name, **fields)  # type: ignore[call-overload]


class _CallableProvider(BaseProvider):
    def __init__(self, name: str, handler: Handler, status: MaturityStatus,
                 health: Optional[Callable[[], bool]] = None) -> None:
        self.name = name
        self.status = status
        self._handler = handler
        self._health = health

    def run(self, payload: BaseModel) -> Dict[str, Any]:
        try:
            result = self._handler(payload.model_dump())
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"external handler '{self.name}' failed: {exc}") from exc
        if not isinstance(result, dict):
            raise ProviderError(f"external handler '{self.name}' must return a dict")
        return result

    def health_check(self) -> HealthStatus:
        if self._health is None:
            return HealthStatus(
                component=f"provider:{self.name}",
                state=HealthState.WARNING,
                detail="external tool — health not reported",
                provider=self.name,
            )
        ok = False
        try:
            ok = bool(self._health())
        except Exception:  # noqa: BLE001
            ok = False
        return HealthStatus(
            component=f"provider:{self.name}",
            state=HealthState.READY if ok else HealthState.FAILED,
            detail="external health probe",
            provider=self.name,
        )


class ExternalToolAdapter(BaseTool):
    def __init__(self, name: str, description: str,
                 input_model: Type[BaseModel], output_model: Type[BaseModel],
                 providers) -> None:
        self.name = name
        self.description = description
        self.status = MaturityStatus.INTEGRATION_READY
        self._input_model = input_model
        self._output_model = output_model
        super().__init__(providers=providers)

    def input_schema(self) -> Type[BaseModel]:
        return self._input_model

    def output_schema(self) -> Type[BaseModel]:
        return self._output_model


def register_external_tool(
    *,
    name: str,
    description: str,
    handler: Handler,
    input_fields: Optional[Dict[str, Tuple[type, Any]]] = None,
    output_fields: Optional[Dict[str, Tuple[type, Any]]] = None,
    health: Optional[Callable[[], bool]] = None,
    status: MaturityStatus = MaturityStatus.INTEGRATION_READY,
    replace: bool = True,
) -> ExternalToolAdapter:
    """Register a new tool at runtime. Returns the created tool."""
    input_model = _model_from_fields(f"{name.title().replace('_', '')}Input", input_fields)
    output_model = _model_from_fields(f"{name.title().replace('_', '')}Output", output_fields)
    provider = _CallableProvider(f"{name}:external", handler, status, health)
    tool = ExternalToolAdapter(name, description, input_model, output_model, [provider])
    tool.status = status
    get_registry().register_tool(tool, replace=replace)
    return tool

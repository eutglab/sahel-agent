"""Tool Registry — discovery, enable/disable, metadata, LLM schema export.

Usage::

    from app.tools.registry import get_registry
    reg = get_registry()
    reg.list()                 # ["sensors", "weather", ...]
    reg.get("weather")         # -> BaseTool
    reg.health_check()          # -> list[HealthStatus]
    reg.describe_for_llm()      # -> [ {name, description, input_schema}, ... ]
    reg.register_tool(my_tool)  # add at runtime (used by the hackathon adapter)
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

from app.core.config import settings
from app.core.errors import ConfigError
from app.core.logging import get_logger
from app.core.schemas import HealthState, HealthStatus, MaturityStatus
from app.tools.base import BaseTool

logger = get_logger("sahel.registry")

# Factories for the built-in tools. Imported lazily so a broken optional tool
# never prevents the registry from loading the core ones.
_BUILTIN_FACTORIES: Dict[str, str] = {
    "vision": "app.tools.vision.tool:build",
    "sensors": "app.tools.sensors.tool:build",
    "weather": "app.tools.weather.tool:build",
    "risk": "app.tools.risk.tool:build",
    "recommendation": "app.tools.recommendation.tool:build",
    "web_search": "app.tools.websearch.tool:build",
    "file_analysis": "app.tools.external.stub_tools:build_file_analysis",
    "notification": "app.tools.external.stub_tools:build_notification",
}


def _load_factory(path: str) -> Callable[[], BaseTool]:
    module_path, _, attr = path.partition(":")
    module = __import__(module_path, fromlist=[attr])
    return getattr(module, attr)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}
        self._load_builtins()

    # --- discovery ---------------------------------------------------- #
    def _load_builtins(self) -> None:
        for name, factory_path in _BUILTIN_FACTORIES.items():
            if not settings.tool_enabled(name):
                logger.info("tool '%s' disabled by config", name)
                continue
            try:
                tool = _load_factory(factory_path)()
            except Exception as exc:  # noqa: BLE001 - a broken optional tool must not kill the app
                logger.warning("could not load tool '%s': %s", name, exc)
                continue
            self._tools[tool.name] = tool
            logger.info("registered tool '%s' [%s]", tool.name, tool.status.value)

    # --- crud ---------------------------------------------------- #
    def register_tool(self, tool: BaseTool, *, replace: bool = False) -> None:
        if tool.name in self._tools and not replace:
            raise ConfigError(f"tool '{tool.name}' already registered")
        self._tools[tool.name] = tool
        logger.info("registered tool '%s' [%s] at runtime", tool.name, tool.status.value)

    def unregister_tool(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise KeyError(f"tool '{name}' is not registered")
        return self._tools[name]

    def has(self, name: str) -> bool:
        return name in self._tools

    def list(self) -> List[str]:
        return sorted(self._tools)

    def tools(self) -> List[BaseTool]:
        return [self._tools[n] for n in self.list()]

    # --- introspection ------------------------------------------------ #
    def metadata(self) -> List[dict]:
        return [t.metadata().model_dump() for t in self.tools()]

    def usable(self) -> List[str]:
        """Tools the agent may actually call (IMPLEMENTED or MOCKED)."""
        ok = {MaturityStatus.IMPLEMENTED, MaturityStatus.MOCKED}
        return [t.name for t in self.tools() if t.status in ok]

    def describe_for_llm(self, only: Optional[List[str]] = None) -> List[dict]:
        specs: List[dict] = []
        for tool in self.tools():
            if only is not None and tool.name not in only:
                continue
            if tool.status not in {MaturityStatus.IMPLEMENTED, MaturityStatus.MOCKED}:
                continue
            specs.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema().model_json_schema(),
                }
            )
        return specs

    def health_check(self) -> List[HealthStatus]:
        results: List[HealthStatus] = []
        for tool in self.tools():
            try:
                results.append(tool.health_check())
            except Exception as exc:  # noqa: BLE001
                results.append(
                    HealthStatus(
                        component=f"tool:{tool.name}",
                        state=HealthState.FAILED,
                        detail=f"health check crashed: {exc}",
                    )
                )
        return results


_REGISTRY: Optional[ToolRegistry] = None


def get_registry(*, refresh: bool = False) -> ToolRegistry:
    global _REGISTRY
    if _REGISTRY is None or refresh:
        _REGISTRY = ToolRegistry()
    return _REGISTRY

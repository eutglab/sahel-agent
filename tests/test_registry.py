from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.core.schemas import MaturityStatus
from app.tools.base import BaseTool


def test_core_tools_registered(registry):
    for name in ["analyze_image", "analyze_sensor_data", "get_weather",
                 "calculate_risk", "generate_recommendation"]:
        assert registry.has(name), name


def test_every_tool_satisfies_contract(registry):
    for tool in registry.tools():
        assert isinstance(tool, BaseTool)
        assert issubclass(tool.input_schema(), BaseModel)
        assert issubclass(tool.output_schema(), BaseModel)
        assert tool.input_schema().model_json_schema()  # serialisable
        assert tool.providers(), f"{tool.name} has no providers"


def test_describe_for_llm_only_exposes_usable(registry):
    specs = registry.describe_for_llm()
    names = {s["name"] for s in specs}
    # INTEGRATION_READY stubs must not be advertised to the LLM.
    assert "analyze_file" not in names
    assert "send_notification" not in names
    # search_web graduated to IMPLEMENTED (Exa-backed) — it is advertised,
    # though the agent only ever triggers it itself once risk is elevated.
    assert "search_web" in names
    assert "analyze_sensor_data" in names
    for s in specs:
        assert {"name", "description", "input_schema"} <= set(s)


def test_runtime_registration_and_unregister(registry):
    class PingInput(BaseModel):
        x: int = 1

    class PingOutput(BaseModel):
        pong: int = 1

    class PingTool(BaseTool):
        name = "ping"
        description = "test tool"
        status = MaturityStatus.MOCKED

        def input_schema(self):
            return PingInput

        def output_schema(self):
            return PingOutput

    from app.tools.base import BaseProvider

    class P(BaseProvider):
        name = "p"

        def run(self, payload):
            return {"pong": 2}

    registry.register_tool(PingTool(providers=[P()]))
    assert registry.has("ping")
    rec = registry.get("ping").execute({"x": 5})
    assert rec.success and rec.output["pong"] == 2
    registry.unregister_tool("ping")
    assert not registry.has("ping")


def test_get_missing_tool_raises(registry):
    with pytest.raises(KeyError):
        registry.get("does_not_exist")

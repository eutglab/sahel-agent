from __future__ import annotations

from app.core.schemas import MaturityStatus
from app.tools.external.adapter import register_external_tool
from app.tools.registry import get_registry


def test_register_external_tool_is_discoverable_and_callable():
    reg = get_registry(refresh=True)
    calls = {"n": 0}

    def handler(payload):
        calls["n"] += 1
        return {"results": [f"hit for {payload.get('query')}"], "source": "fake-search"}

    register_external_tool(
        name="hackathon_search",
        description="Fake external search for tests",
        handler=handler,
        input_fields={"query": (str, ...)},
        output_fields={"results": (list, ...), "source": (str, "")},
        status=MaturityStatus.MOCKED,  # so the agent may actually call it
    )

    assert reg.has("hackathon_search")
    assert "hackathon_search" in {s["name"] for s in reg.describe_for_llm()}

    rec = reg.get("hackathon_search").execute({"query": "soil moisture"})
    assert rec.success
    assert rec.output["results"] == ["hit for soil moisture"]
    assert calls["n"] == 1

    reg.unregister_tool("hackathon_search")


def test_external_handler_failure_is_captured_not_raised():
    reg = get_registry(refresh=True)

    def bad_handler(payload):
        raise ValueError("upstream down")

    register_external_tool(
        name="flaky_tool",
        description="raises",
        handler=bad_handler,
        input_fields={"q": (str, "")},
    )
    rec = reg.get("flaky_tool").execute({"q": "x"})
    assert not rec.success
    assert "upstream down" in (rec.error or "")
    reg.unregister_tool("flaky_tool")

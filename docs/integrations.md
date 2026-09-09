# Integrations

Two ways to give the agent a new capability.

## A. Drop-in tool folder (compile-time)

```
app/tools/my_tool/
  tool.py       # class MyTool(BaseTool): name, description, status, input/output_schema
  schema.py     # MyToolInput, MyToolOutput  (pydantic)
  providers/
    real.py     # class MyRealProvider(BaseProvider): run(), health_check()
    mock.py     # terminal MOCKED provider
```

Then register the factory in `app/tools/registry.py::_BUILTIN_FACTORIES`
(`"my_tool": "app.tools.my_tool.tool:build"`) and add
`TOOL_MY_TOOL_ENABLED=true` to `.env`.

## B. `register_external_tool` (runtime — the hackathon fast path)

```python
from app.core.schemas import MaturityStatus
from app.tools.external.adapter import register_external_tool

def handler(payload: dict) -> dict:
    r = call_organiser_api(payload["query"])          # your code
    return {"results": r["items"], "source": "acme"}

register_external_tool(
    name="hackathon_search",
    description="Search the organiser's environmental knowledge base",
    handler=handler,
    input_fields={"query": (str, ...)},
    output_fields={"results": (list, ...), "source": (str, "")},
    status=MaturityStatus.MOCKED,   # MOCKED/IMPLEMENTED => agent may call it; INTEGRATION_READY => registry-only
)
```

The registry now lists `hackathon_search`; `describe_for_llm()` includes it (if
status is MOCKED/IMPLEMENTED) so the L1 agent can call it; handler exceptions are
captured on the `ToolCallRecord`, never raised into the loop.

## FUTURE interface signatures (not implemented)

These are the shapes we would implement next; calling them today raises
`NotIntegratedError`.

```python
search_web(query: str, max_results: int = 5) -> {results: list, source: str}
analyze_file(filename: str, content_b64: str) -> {summary: str, fields: dict}
send_notification(message: str, channel: str) -> {delivered: bool, channel: str}

get_satellite_data(latitude: float, longitude: float, date: str | None) -> {...}
analyze_location(latitude: float, longitude: float) -> {...}     # geospatial context
get_sensor_data(device_id: str) -> SensorReadings                # live IoT pull
speech_to_text(audio: bytes) -> {text: str}
text_to_speech(text: str) -> {audio: bytes}
query_dataset(name: str, filters: dict) -> {rows: list}
```

## Health & pre-flight

- `python healthcheck.py` — config, registry, agent, per-tool provider health,
  optional integrations (informational), demo assets. Exit 0 unless a **core**
  tool failed.
- `python scripts/test_integrations.py` — schema round-trip, provider health,
  canned smoke execution, fallback availability. INTEGRATION_READY-but-unconfigured
  shows as `NOT CONFIGURED`, not a failure.

# Innovation statement

Not "because it uses AI." Four concrete, demonstrable claims:

## 1. Agentic orchestration you can prove live

The agent selects tools from a **registry it introspects** (`describe_for_llm()`),
not a hard-coded sequence. It skips tools whose modality is absent and says so in
the trace. And `register_external_tool(...)` adds a capability **at runtime** that
the agent then discovers and uses — shown on stage, not on a slide.
*Evidence: `app/tools/registry.py`, `tests/test_external_adapter.py`, the Agent
activity panel.*

## 2. Multimodal fusion that changes the decision

`calculate_risk` consumes the merged `ObservationBundle`. When sensors, image and
weather corroborate, `cross_check` adds converging-evidence, nudges the combined
score up and raises confidence; when they conflict, it flags a warning and lowers
confidence. The same sensor values yield a *different* result depending on the
other modalities.
*Evidence: `app/tools/risk/rules.py::_cross_check`, `tests/test_risk.py`.*

## 3. Explainable, honestly-labelled tool use

Every tool and provider carries `IMPLEMENTED / MOCKED / INTEGRATION_READY /
FUTURE`, surfaced in the UI and `healthcheck.py`. The Run details tab shows the
provider that answered, per-tool latency, and the full trace. No feature is faked
to look more finished than it is.
*Evidence: `MaturityStatus`, `ToolMetadata`, `docs/limitations.md`.*

## 4. Resilience as a design property

Three-level graceful degradation (LLM → rule-based planner → precomputed),
per-tool fallback chains that report their source, real providers that self-skip
offline, and a `$0` / no-key default. Built for low-resource settings where the
network and APIs are not guaranteed.
*Evidence: `app/agent/agent.py`, `tests/test_offline.py`, `tests/test_agent.py`
fallback cases.*

## What we did NOT claim

No trained model, no RAG, no real IoT/satellite/notification delivery, no offline
edge model. Those are FUTURE interfaces or roadmap — see `docs/roadmap.md`.

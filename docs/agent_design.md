# Agent design

## Why this is an agent, not a chatbot

A chatbot is `input → LLM → text`. SAHEL Agent instead:

1. **Perceives** several modalities and inventories what is actually available
   (`AgentInput.available_modalities()`).
2. **Reasons** about which tools are relevant — and which are *not* (it will not
   call `get_weather` without a location, and says so in the trace).
3. **Acts** by executing tools it selected from a registry it can introspect.
4. **Observes** each `ToolCallRecord`, including which provider answered and why.
5. **Re-plans** if needed (bounded loop; L1 can re-ask after seeing results).
6. **Cross-checks** evidence across modalities in `calculate_risk`.
7. **Synthesises** a structured recommendation and **explains** itself via the trace.

The decisive, demonstrable difference: the **Agent activity** panel shows the
tool-selection and execution steps live, and adding a tool at runtime
(`register_external_tool`) makes the agent able to use it with no code change.

## The loop

```
receive AgentInput
  → detect modalities
  → pick reasoning mode:
        L1  llm.complete_with_tools(system, context, registry.describe_for_llm())
        L2  planner.plan_tools(input, usable_tools)
  → run selected observation tools (analyze_image / analyze_sensor_data / get_weather)
  → run calculate_risk on the merged bundle          (backbone, always)
  → run generate_recommendation on all outputs       (backbone, always)
  → build ObservationBundle + AgentResult + trace + run log
```

`AGENT_MAX_ITERATIONS` (default 6) bounds the L1 re-ask loop.

## Tool selection rules (L2 planner — fully transparent)

| Condition | Tool added |
|---|---|
| image present | `analyze_image` |
| any sensor field present | `analyze_sensor_data` |
| location label or lat/lon present | `get_weather` |
| always (if registered) | `calculate_risk`, then `generate_recommendation` |

L1 (LLM) may choose differently, but the agent still **filters** its choices:
a tool requested for an absent modality is skipped and noted in the trace.

## Multimodal fusion

`app/agent/synthesis.py` merges tool outputs into one `ObservationBundle`.
`calculate_risk` consumes the *whole* bundle:

- **Converging evidence** (e.g. low soil moisture *and* image discolouration *and*
  dry forecast) → `cross_check.confidence_adjustment` up, combined score nudged up.
- **Diverging evidence** (image looks healthy but sensors say stressed) → flagged
  as a warning, confidence nudged down.

This is why the same sensors produce a *higher* combined risk when a corroborating
image is present — fusion changes the output, it is not decorative.

## Anti-hallucination measures

- Tool outputs are Pydantic-validated; a malformed provider response is rejected
  and the next provider (or the deterministic path) is used.
- The recommendation LLM provider receives **only structured tool outputs** and is
  instructed not to invent numbers; missing fields are back-filled from the
  deterministic template.
- Risk figures are always labelled *prototype indicator*; vision output is always
  *possible signs*, never a diagnosis.
- Private chain-of-thought is never surfaced — only step summaries in the trace.

## Explainability surfaces

| Surface | Content |
|---|---|
| Agent activity / trace | ordered steps: understanding, tool calls, provider used, done/failed |
| Risk assessment tab | every sub-score with its **named drivers** + cross-check |
| Run details tab | provider map, per-tool latency, raw result JSON, full trace |
| `logs/runs.jsonl` + SQLite | one machine-readable row per run |

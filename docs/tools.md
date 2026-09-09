# Tools

Every tool implements `BaseTool` (`app/tools/base.py`):

```python
name: str
description: str
status: MaturityStatus
input_schema()  -> type[BaseModel]
output_schema() -> type[BaseModel]
execute(raw_input) -> ToolCallRecord   # runs the provider fallback chain
health_check()  -> HealthStatus
metadata()      -> ToolMetadata
```

`execute()` never raises on provider failure — the outcome is on the returned
`ToolCallRecord` (`success`, `provider_used`, `source_note`, `output`, `error`).

---

## `analyze_image`  — IMPLEMENTED

Cautious visual analysis of a plant/field photo.

**Input:** `image_bytes: bytes`, `hint: str = ""`
**Output:** `observations[]`, `possible_signs[]`, `confidence` (0–1), `limitations[]`, `method`

**Providers (chain):** `llm_vision` → `local_heuristic` → `mock`

- `local_heuristic` (offline, IMPLEMENTED): resizes to 160×160, computes green /
  yellow-brown / dark pixel fractions + brightness, emits *possible* signs. Colour
  statistics only — **not** plant pathology.
- `llm_vision` (INTEGRATION_READY): real multimodal call via the active `LLMClient`;
  self-skips in offline/mock mode.

Never returns a diagnosis. Wording is constrained to "possible", "compatible with",
"requires field confirmation".

---

## `analyze_sensor_data`  — IMPLEMENTED

**Input:** `temperature_c?`, `soil_moisture_pct?`, `air_humidity_pct?`,
`rainfall_mm?`, `growth_stage`
**Output:** `risk_level` (low/moderate/elevated/high), `indicators[]`,
`anomalies[]`, `explanation[]`, `missing_fields[]`, `method`

**Provider:** `rules` (deterministic). Thresholds live in
`app/data/thresholds.yaml` and are reloaded on every call (edit freely).
Growth-stage sensitivity: low soil moisture at `flowering`/`fruiting` escalates
harder. Missing inputs are reported, never guessed.

---

## `get_weather`  — IMPLEMENTED

**Input:** `label?`, `latitude?`, `longitude?`
**Output:** `source`, `temperature_c`, `humidity_pct`, `rainfall_mm`,
`rain_probability`, `forecast[]` (3 days), `note`

**Providers (chain, configurable):** `open_meteo` → `local` → `mock`

- `open_meteo` (IMPLEMENTED): free, **no API key**, needs lat/lon; self-skips
  offline; `ProviderTimeout`/`ProviderUnavailable` on any network issue.
- `local` (IMPLEMENTED): bundled records in `demo_data/weather/index.json`,
  keyed by fictional location label.
- `mock` (MOCKED): deterministic synthesis from a hash of the location — terminal
  provider so the demo always has weather.

---

## `calculate_risk`  — IMPLEMENTED (prototype heuristic)

**Input:** merged `sensors?`, `vision?`, `weather?`, `growth_stage`
**Output:** `water_stress`, `heat_stress`, `environmental`, `combined_risk`
(each: `score` 0–1, `level`, `drivers[]`), `cross_check`
(`converging_evidence[]`, `diverging_evidence[]`, `confidence_adjustment`),
`confidence`, `disclaimer`

**Provider:** `heuristic`. Transparent weighted sum (weights in `thresholds.yaml`).
Each point added to a sub-score carries a **named driver**. Not a validated model —
the output always includes a disclaimer.

---

## `generate_recommendation`  — IMPLEMENTED

**Input:** `sensors?`, `vision?`, `weather?`, `risk?`, `growth_stage`, `modalities[]`
**Output:** `priority` (low/medium/high), `main_finding`, `recommended_actions[]`,
`monitoring_actions[]`, `warnings[]`, `confidence`, `limitations[]`, `method`

**Providers (chain):** `template` → `llm`  *(config default `template` first; set
`RECOMMENDATION_PROVIDER=llm` to prefer the model)*

- `template` (IMPLEMENTED): deterministic mapping risk levels + anomalies →
  prioritised actions. Always attaches a "decision support, not advice" warning.
- `llm` (INTEGRATION_READY): grounded synthesis on structured inputs only; missing
  keys back-filled from the template; self-skips offline/mock.

---

## INTEGRATION_READY stubs (disabled by default)

`search_web`, `analyze_file`, `send_notification` — real `BaseTool` contract,
registered only when `TOOL_<NAME>_ENABLED=true`, and their provider raises
`NotIntegratedError`. They demonstrate the extension surface without pretending
to work.

## FUTURE interfaces (documented, not built)

`get_satellite_data`, `analyze_location`, `get_sensor_data`, `speech_to_text` /
`text_to_speech`. Signatures are in [`integrations.md`](integrations.md).

## Adding a tool

Either drop a folder under `app/tools/<name>/` (`tool.py`, `schema.py`,
`providers/`) and add it to `_BUILTIN_FACTORIES` in `registry.py`, **or** call
`register_external_tool(...)` at runtime (see [`integrations.md`](integrations.md)).

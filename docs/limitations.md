# Limitations

Stated plainly so a judge never has to guess.

## Scientific

- **The risk score is a prototype indicator**, produced by transparent weighted
  heuristics in `app/data/thresholds.yaml` + `app/tools/risk/rules.py`. It is
  **not** a validated agronomic model. Thresholds are generic and need local
  calibration.
- **Vision output is "possible signs", never a diagnosis.** The offline provider
  is colour statistics (green / yellow-brown / dark pixel fractions), not plant
  pathology. It is sensitive to lighting, camera, background and framing.
- Recommendations are **decision support**, not agronomic advice. Every
  recommendation carries that warning.

## Technical

- The default reasoning path is the **deterministic planner** (rule-based). The
  LLM tool-calling path is real but only active with a configured non-mock
  provider and network.
- `MockLLMClient` is not a language model — it is a deterministic stand-in that
  gives the agent a working tool-calling loop offline. Clearly labelled `MOCKED`.
- Weather in demo mode is a bundled local dataset or synthetic values, not a live
  observation.
- No calibration of confidence values against ground truth — they are heuristic.
- Single-user local app; no auth, no concurrency guarantees, no rate limiting.

## Data

- All demo data is synthetic and fictional. No real locations, farms, people, or
  organisations are represented.
- The local run log stores a run *summary* (see [`../PRIVACY.md`](../PRIVACY.md)),
  not raw form inputs, and never leaves the machine.

## Scope explicitly excluded (this MVP)

Multi-agent orchestration · RAG · trained image classifier / fine-tuning ·
real IoT hardware · real satellite pipeline · real notification delivery ·
mobile / native app · live voice · authentication · Docker/K8s/queues/servers.
These appear as FUTURE interfaces or in [`roadmap.md`](roadmap.md) only.

## Honesty taxonomy

| Tag | Meaning | Examples |
|---|---|---|
| `IMPLEMENTED` | real code, works offline, tested | sensors, risk, weather(local/open_meteo), vision(local), recommendation(template) |
| `MOCKED` | real interface, synthetic data by design | `MockLLMClient`, `mock` weather/vision |
| `INTEGRATION_READY` | contract + adapter slot, not wired live | anthropic/openai/hackathon LLM, `llm_vision`, `llm` recommendation, `search_web`/`analyze_file`/`send_notification` |
| `FUTURE` | interface documented, no implementation | satellite, geospatial, IoT pull, voice, edge, robotics |

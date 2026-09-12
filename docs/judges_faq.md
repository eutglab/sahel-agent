# Judge FAQ

Answers distinguish **IMPLEMENTED / MOCKED / INTEGRATION_READY / FUTURE**.

### 1. Why is this an AI agent and not a chatbot?
It runs a loop: perceive modalities → select tools from a registry it can
inspect → execute them through provider adapters → observe results → cross-check →
synthesise. Tool selection is dynamic and **visible** in the Agent activity panel.
A chatbot is a single `input → model → text` call; this is not.

### 2. Why not just use a chatbot / one big prompt?
A single prompt can't run a colour heuristic on an image, hit a weather API, apply
configurable thresholds, and combine them with a transparent scoring function —
and it can't *show its work* per step or degrade gracefully when a service is
down. The tool architecture also makes new capabilities pluggable.

### 3. What tools does it use?
`analyze_image`, `analyze_sensor_data`, `get_weather`, `calculate_risk`,
`generate_recommendation` (all IMPLEMENTED). Plus INTEGRATION_READY stubs
(`search_web`, `analyze_file`, `send_notification`) and FUTURE interfaces
(satellite, geospatial, IoT pull, voice).

### 4. How does the agent decide which tool to use?
Two paths. **L2 (default, rule-based):** tool per present modality — no image ⇒ no
`analyze_image`, no location ⇒ no `get_weather`. **L1 (with a real LLM):** the
model is given the tool schemas and chooses; the agent still filters out choices
for absent modalities and logs that it did.

### 5. How do you prevent hallucinations?
Pydantic-validated tool I/O with fallback on failure; the recommendation LLM sees
only structured tool outputs and is told not to invent numbers, with missing
fields back-filled deterministically; risk is always labelled a prototype
indicator; vision output is always "possible signs", never a diagnosis.

### 6. What happens if an API is unavailable?
Per-tool fallback chain (`real → local → mock`), then, if the whole reasoning path
fails, a frozen precomputed scenario result, then a deterministic-planner retry.
The UI always shows which source answered. There is no bare "API ERROR" state.

### 7. How much does it cost?
Demo: **$0**, no key, no network. Real LLM usage is pay-per-use under your key;
we have **not measured** a per-run figure and don't quote one. Open-Meteo weather
is free. See `docs/cost.md`.

### 8. Can it work offline?
Yes — that's the default. `pytest -m offline` runs the whole agent with every
socket blocked and all 5 scenarios still complete.

### 9. What data did you use?
Only synthetic/fictional data: procedurally generated images, hand-authored sensor
values, fictional location names. No real farms, people, or organisations.

### 10. How do you validate the system?
75 automated tests (unit, contract, agent behaviour, resilience, offline) plus
`healthcheck.py`, `scripts/test_integrations.py`, and a local `benchmark`. We do
**not** validate agronomic correctness — that's out of scope.

### 11. Is the recommendation scientifically validated?
No. It is a transparent prototype heuristic and is labelled as such everywhere.
It requires local calibration and field confirmation by a qualified person.

### 12. Can this connect to IoT?
The interface `get_sensor_data(device_id)` is defined (FUTURE). Wiring it to a
real broker is Phase 2. Today you'd pull readings externally and pass them in, or
register a live puller with `register_external_tool`.

### 13. Can this work on mobile?
Not as a native app (excluded from the MVP). The Streamlit UI is responsive-ish;
a proper mobile/voice client is Phase 4.

### 14. Can this use satellite data?
`get_satellite_data(lat, lon, date)` is a documented FUTURE interface. Not
implemented. It would enter as another evidence source in `calculate_risk`.

### 15. What is the real-world impact?
It shows how fragmented environmental signals can be combined by an agent that
picks the right tools and explains itself — designed for low-resource settings
(offline-first, $0 path, modular). Impact claims beyond that would be unverified.

### 16. What did you actually build?
See `docs/architecture.md` §4 and the BUILD STATUS in the final report: the agent
loop, tool registry, provider abstraction, 5 working tools, trace + run log,
3-level fallback, 5 demo scenarios, the external-tool adapter, health + preflight
scripts, 75 tests, and full docs.

### 17. What is genuinely innovative?
See `docs/innovation.md`: (a) live-provable extensibility via the registry +
`register_external_tool`, (b) the honesty taxonomy surfaced in the UI, (c)
multimodal fusion that measurably changes the risk output, (d) resilience as a
design property, not an afterthought.

### 18. What would you build next?
Phase 2: implement `get_sensor_data` against a real broker + streaming sensor
analysis + a real notification channel. Then satellite evidence in the risk
calculator.

### 19. What happens if the LLM is unavailable?
`get_llm_client()` returns the deterministic `MockLLMClient`; the agent runs the
rule-based planner (L2). The trace says `rule-based planner`. Output is still
complete.

### 20. Can another provider be plugged in?
Yes. LLM: set `LLM_PROVIDER` + a key (Anthropic/OpenAI/OpenAI-compatible
hackathon endpoint). Weather/vision/recommendation: fill the `hackathon.py`
provider skeleton and add it to the fallback chain. Any external service: one
`register_external_tool(...)` call, no core changes.

### 21. How quickly can you add a new tool?
Runtime: a single `register_external_tool` call (< 10 min incl. mapping the
response). Compile-time: a folder + a registry line. `test_external_adapter.py`
proves the runtime path.

### 22. What did you deliberately NOT build, and why?
Multi-agent, RAG, trained CV model, real IoT/satellite/notifications, auth,
Docker/K8s/queues. Reason: time, and "working demo > architecture". They're
FUTURE interfaces or roadmap items, not fake features.

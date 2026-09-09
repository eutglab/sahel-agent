# AI transparency

Exactly what is AI / LLM / tool-calling / rule-based / heuristic / deterministic /
mock in SAHEL Agent. Nothing here is blended or overstated.

| Component | Technology | Real / Mock | Role |
|---|---|---|---|
| **Agent loop** (`app/agent/agent.py`) | Plain Python control flow | Real | Orchestrates perception → tool selection → execution → cross-check → synthesis; owns the 3-level fallback |
| **Tool selection — L1** | LLM function/tool calling (Anthropic / OpenAI / OpenAI-compatible) | Real **when a key is set**; otherwise not used | The model is given tool JSON schemas and returns tool calls; a bounded re-ask loop lets it request more after seeing results |
| **Tool selection — L2 (default)** | Deterministic rules (`app/agent/planner.py`) | Real | Picks one tool per present modality; this is the path that runs in demo/offline mode |
| **Tool selection — L3** | Static file load | Real | Serves a frozen precomputed result if the reasoning path throws |
| **`MockLLMClient`** | Deterministic string logic (`app/llm/providers/mock.py`) | **Mock** | Stands in for an LLM so the tool-calling loop works with no key/network; reads `AVAILABLE MODALITIES` and returns a fixed plan. **Not a language model.** |
| **`analyze_image` — local** | Colour-histogram heuristic with NumPy/Pillow (`local_heuristic.py`) | Real (heuristic) | Green / yellow-brown / dark pixel fractions + brightness → *possible* signs. **No ML model. No training. Not plant pathology.** |
| **`analyze_image` — llm_vision** | Multimodal LLM call | Real when a non-mock LLM is active; else self-skips | Sends the image to the model with a cautious prompt; output parsed to the same schema |
| **`analyze_image` — mock** | Hash-seeded canned text | **Mock** | Terminal fallback only |
| **`analyze_sensor_data`** | Configurable threshold rules (`thresholds.yaml` + `sensors/rules.py`) | Real (rule-based) | Compares readings to prototype ranges; flags anomalies; drops physically implausible values |
| **`get_weather` — open_meteo** | HTTP call to Open-Meteo | Real | Live forecast; free, no key; self-skips offline |
| **`get_weather` — local** | Bundled JSON dataset | Real (static data) | Offline weather for fictional locations |
| **`get_weather` — mock** | Hash-seeded synthesis | **Mock** | Terminal fallback; labelled `demo (synthetic, deterministic)` in its output |
| **`calculate_risk`** | Transparent weighted heuristic (`risk/rules.py`) | Real (heuristic, **prototype**) | Water / heat / environmental sub-scores with named drivers; cross-check of converging/diverging evidence; **not a validated model** |
| **`generate_recommendation` — template** | Deterministic mapping rules | Real (rule-based) | Risk levels + anomalies → prioritised actions; always attaches warnings + limitations |
| **`generate_recommendation` — llm** | LLM synthesis grounded on structured tool outputs | Real when a non-mock LLM is active; else self-skips | Rewrites the structured result in prose; forbidden from inventing numbers; missing fields back-filled from the template |
| **`search_web` / `analyze_file` / `send_notification`** | — | **Not implemented** | INTEGRATION_READY stubs; raise `NotIntegratedError` |
| **satellite / geospatial / IoT pull / voice** | — | **Not implemented** | FUTURE; interface signatures only (`docs/integrations.md`) |
| **Agent trace / run log** | Plain Python + SQLite/JSONL | Real | Records the actual steps + provider used per tool |

## One-line summary per claim

- "It's an AI agent" → **true**: it selects and orchestrates tools in a loop and shows its work. The *selection* is LLM-driven with a key, rule-based without.
- "It uses an LLM" → **true when configured**; the default demo runs on a deterministic mock, clearly labelled.
- "It analyses images" → **true**, via a colour heuristic offline (not a trained model) or an LLM with a key.
- "It uses real weather" → **true** with `WEATHER_PROVIDER=open_meteo`; otherwise local/synthetic and labelled as such.
- "It calculates risk" → **true**, with a documented prototype heuristic — not a validated agronomic model.
- "It works offline" → **true**; proven by `pytest -m offline` with all sockets blocked.
- "It's extensible" → **true**; `register_external_tool()` adds a tool at runtime (test: `test_adversarial`/`test_external_adapter`).

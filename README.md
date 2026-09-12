# SAHEL Agent

**Multimodal AI Agent for Environmental & Agricultural Intelligence**

An independent AI-agent prototype built for a hackathon. It observes multiple
kinds of environmental information (an image, sensor readings, a location, a
growth stage), **decides which specialised tools to use**, runs them, **cross-checks
their results**, and turns the combined evidence into an **actionable
recommendation** with an explicit confidence score and limitations.

> It is not a chatbot with buttons. It is an agent that *selects and orchestrates
> tools*, and shows you exactly what it did.

```
OBSERVE  →  REASON  →  USE TOOLS  →  CROSS-CHECK  →  RECOMMEND
```

---

## Overview

| | |
|---|---|
| **What** | A single, well-designed AI agent with a tool registry + provider abstraction |
| **For what** | Environmental / agricultural decision *support* (not advice) |
| **How** | Multimodal inputs → dynamic tool selection → specialised tools → fused analysis |
| **Runs** | Fully offline, **$0**, **no API key** (mock LLM + local providers by default) |
| **Extensible** | New tool = new folder or one `register_external_tool(...)` call |

## Problem

In many agricultural and environmental settings the information needed to make a
decision is **fragmented**: a photo here, sensor values there, weather somewhere
else, all analysed separately. SAHEL Agent combines them and automatically uses
the right tools to produce one exploitable analysis.

## Solution

A multimodal agent that:

1. inventories which modalities are actually present,
2. selects the tools that make sense (no fixed pipeline),
3. executes them through a **provider abstraction** with a configurable fallback
   chain (`real → local → demo`),
4. fuses the outputs into one `ObservationBundle`,
5. runs an explainable prototype **risk heuristic** with a cross-check step,
6. synthesises a prioritised recommendation,
7. records a visible **agent trace** and one run log per analysis.

## Why Agentic AI?

| Simple chatbot | SAHEL Agent |
|---|---|
| `User → LLM → text` | `User → agent → decision → tool selection → tool execution → observation → (more tools) → cross-check → recommendation` |
| One model call | A bounded loop over a **tool registry** it can inspect |
| Opaque | Every step shown in the trace; each tool tagged `IMPLEMENTED / MOCKED / INTEGRATION_READY / FUTURE` |
| Breaks when the API is down | 3-level graceful degradation; works with no network |

See [`docs/agent_design.md`](docs/agent_design.md).

## Architecture

```
UI (Streamlit)
      │
      ▼
  SahelAgent ──────────────► AgentTrace + RunLogger (SQLite / JSONL)
      │  reasoning loop
      │   L1  LLM tool-calling   (real model picks tools)
      │   L2  Deterministic planner (rule-based selection)
      │   L3  Precomputed scenario  (frozen result)
      ▼
  Tool Registry ──► BaseTool ──► Provider fallback chain ──► External service
   analyze_image        (real / local / mock / hackathon adapters)
   analyze_sensor_data
   get_weather
   calculate_risk
   generate_recommendation
   + register_external_tool(...)   ← hackathon fast path
```

Full detail: [`docs/architecture.md`](docs/architecture.md).

## Features

- Dynamic, modality-driven tool selection (no hard-coded pipeline)
- Tool Registry with runtime registration + `describe_for_llm()`
- Provider abstraction + per-tool configurable fallback chains
- Multimodal fusion that *changes the output* (converging evidence → higher risk & confidence)
- Explainable prototype risk indicators with named drivers + cross-check
- Visible agent trace + per-run observability (Run Details tab)
- 3-level graceful degradation; **offline-first** by default
- `healthcheck.py` + `scripts/test_integrations.py` pre-flight checks
- 5 demo scenarios + one-click "Load Demo Scenario"
- EN / FR / Bambara language switcher for the UI chrome ([`docs/i18n.md`](docs/i18n.md) — scope disclosed honestly)
- Risk-first result layout (assessment → why → actions → evidence) with technical detail behind progressive disclosure, not up front
- **Ask the Agent** — a grounded Q&A panel over the current analysis; deterministic by default, a real LLM when one is configured, and able to trigger `search_web` itself if a question needs evidence the pipeline didn't already fetch
- 104 automated tests incl. an offline suite that blocks all sockets

## Tools

| Tool | Purpose | Real provider | Offline provider | Status |
|---|---|---|---|---|
| `analyze_image` | cautious visual observations, possible signs | LLM vision | local colour heuristic (Pillow) / mock | IMPLEMENTED |
| `analyze_sensor_data` | thresholds → risk level, anomalies, explanation | — (rules) | rules (`thresholds.yaml`) | IMPLEMENTED |
| `get_weather` | current + short forecast | **Open-Meteo** (free, keyless) | local dataset / synthetic | IMPLEMENTED |
| `calculate_risk` | water / heat / environmental / combined + cross-check | — (heuristic) | heuristic | IMPLEMENTED |
| `generate_recommendation` | prioritised actions, monitoring, warnings | LLM (grounded) | deterministic template | IMPLEMENTED |
| `search_web` | grounds an elevated risk finding in live evidence, with citations | **Exa** | offline sample sources | IMPLEMENTED |
| `analyze_file`, `send_notification` | — | — | raise `NotIntegratedError` | INTEGRATION_READY (disabled) |
| geospatial / satellite / IoT / voice | — | — | — | FUTURE (interface only) |

Details: [`docs/tools.md`](docs/tools.md), [`docs/providers.md`](docs/providers.md).

## Installation

```bash
git clone <repo> sahel-agent && cd sahel-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/seed_demo.py        # generate synthetic demo assets (idempotent)
```

Requires Python 3.10+.

## Configuration

Everything is optional. Copy the template and edit only what you need:

```bash
cp .env.example .env
```

Key switches:

| Variable | Default | Meaning |
|---|---|---|
| `ENVIRONMENT` | `demo` | `demo` / `hackathon` / `real` |
| `DEMO_MODE` | `true` | prefer local/mock providers, no keys |
| `LLM_PROVIDER` | `mock` | `mock` / `anthropic` / `openai` / `openrouter` / `hackathon` |
| `WEATHER_PROVIDER` | `local` | `open_meteo` / `local` / `mock` / `hackathon` |
| `WEB_SEARCH_PROVIDER` | `exa` | `exa` / `mock`; needs `EXA_API_KEY` for live evidence |
| `*_FALLBACK_CHAIN` | see file | ordered provider fallback per capability |

Secrets go in `.env` only (gitignored). Never in code. See [`SECURITY.md`](SECURITY.md).

### Running with a real LLM (OpenRouter)

By default the agent reasons with the free, offline `mock` LLM. To let it use a
real model via [OpenRouter](https://openrouter.ai) for LLM tool-calling (L1) and
for **Ask the Agent**'s grounded answers:

```bash
pip install openai            # OpenRouter's endpoint is OpenAI-compatible
```

```env
# .env
ENVIRONMENT=real
DEMO_MODE=false
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=your_model_here   # pick one from https://openrouter.ai/models
```

Both `DEMO_MODE=false` **and** `ENVIRONMENT` != `demo` are required — either one
left at its default keeps the agent fully offline (`settings.offline_first`),
which is the deliberate safety net: a missing/invalid key or model, a timeout,
an HTTP error, or an empty/malformed response all fall back to the deterministic
planner / mock automatically, never a crash. Verify before a demo:

```bash
python scripts/test_integrations.py   # reports OpenRouter health, never prints the key
```

Deterministic risk calculation (`calculate_risk`) never delegates to the LLM —
OpenRouter only ever affects tool selection and wording, never the risk numbers.

## Demo

```bash
make demo        # or: streamlit run ui/streamlit_app.py
```

1. Open the app → sidebar → **Load demo scenario** → *Scenario 4 — Multiple risk factors*.
2. Press **Analyze Field**.
3. Read top-down: risk level → main driver → why → recommended actions → evidence.
4. Open **View Details** for the full technical picture (six categories, live trace, raw JSON) — kept, just no longer first.
5. Try **💬 Ask the Agent** — "Why is the risk moderate?", "What should I do first?", "Show me the evidence."

Target: under 60 seconds from launch to a full result. Script: [`docs/demo.md`](docs/demo.md).

## Example

```python
from app.agent.agent import run_agent
from app.core.schemas import AgentInput, Location, SensorReadings

result = run_agent(AgentInput(
    sensors=SensorReadings(temperature_c=37, soil_moisture_pct=18,
                           air_humidity_pct=31, rainfall_mm=0, growth_stage="flowering"),
    location=Location(label="Fictional Site Alpha", latitude=14.5, longitude=-4.2),
))
print(result.reasoning_mode, result.tools_used)
print(result.observation.risk["combined_risk"]["level"])
print(result.recommendation["priority"], result.recommendation["main_finding"])
```

## Testing

```bash
make test              # pytest -m "not integration"   (104 tests)
pytest -m offline      # offline guarantee (sockets blocked)
python healthcheck.py
python scripts/test_integrations.py
python benchmark/run_benchmark.py
```

[`docs/testing.md`](docs/testing.md) · [`docs/benchmark.md`](docs/benchmark.md) · [`docs/ai_transparency.md`](docs/ai_transparency.md) · [`docs/final_scorecard.md`](docs/final_scorecard.md) · [`docs/top_10_risks.md`](docs/top_10_risks.md) · [`docs/final_demo_script.md`](docs/final_demo_script.md)

## Limitations

The risk numbers are **prototype indicators from transparent heuristics**, not a
validated agronomic model. Vision output is *possible signs*, never a diagnosis.
Full list: [`docs/limitations.md`](docs/limitations.md).

## Privacy

Runs on synthetic/fictional data. Uploaded images are held in memory for the
analysis and **not persisted**. See [`PRIVACY.md`](PRIVACY.md).

## Roadmap

Phase 1 (this MVP) → IoT streaming → satellite/geospatial → voice → edge AI →
autonomous environmental agents → physical AI. All future phases are documented,
none are claimed as built. See [`docs/roadmap.md`](docs/roadmap.md).

## Future Research

Low-resource agent orchestration, on-device fallback reasoning, cross-modal
evidence weighting, and calibrated uncertainty for environmental heuristics.

## Team — EUTG-Bot-Lab

| Name | Role | Contact |
|---|---|---|
| **Hamed Diawara** | **Team Lead** & Agent Architecture — reasoning pipeline, tool registry, fallback design | hameddiawara23@gmail.com · +223 79 45 18 36 |
| Virgile Fred ADINGBANNON | LLM & Provider Integration — OpenRouter/LLM adapters, fallback chains | adingbannonfred@gmail.com · +223 77 32 67 98 |
| Aminata Baye Konaké | UI/UX & Demo Experience — Streamlit interface, risk-first design | amia92098@gmail.com · +223 60 24 12 09 |
| Alfousseyni Coulibaly | Testing, QA & Documentation — test suite, docs, judge-facing materials | lmgalfous@gmail.com · +223 50 96 34 46 |

## License

Apache-2.0 — see [`LICENSE`](LICENSE). Chosen over MIT for its explicit patent
grant, which suits a platform meant to accept third-party tool integrations.

# Final demo script (3 minutes, judge-facing)

## Setup (before you walk on)

```bash
cd sahel-agent && source .venv/bin/activate
DEMO_JUDGE_MODE=true make demo
```

The app opens with **Scenario 4 — Multiple risk factors** preloaded and a banner:
*"Press ANALYZE to run the agent."* One spare terminal ready with plain `make demo`.

---

## 0:00–0:20 — Problem

> "To make an environmental decision you need a photo, sensor readings, weather,
> and local context — and today they're looked at separately. SAHEL Agent is an
> agent that pulls them together and decides which tools to use."

Point at the sidebar: *Environment: demo · LLM: mock · runs offline, no key.*

## 0:20–0:40 — Input

> "One scenario is loaded: a plant photo, 37 °C, soil moisture 18 %, air humidity
> 31 %, no rainfall, flowering stage, a location."

Scroll the Input panel so they see it's real structured input, not a prompt box.

## 0:40–1:20 — Agent activity (the core beat)

Press **ANALYZE**. Read the **Agent activity** list aloud as it appears:

> "It understood the input, then *chose* its tools — vision, sensor analysis,
> weather — ran them, and only then the risk calculator and the recommendation.
> No fixed pipeline: with no location it would skip weather, and it tells you so."

## 1:20–2:10 — Decision support

Open the tabs in order:

- **Risk assessment** → "Water stress **high**, heat stress **high** — each line
  shows *why* (its drivers)."
- **Cross-check** → "Sensors, image and weather all point the same way — that's
  *converging evidence*, so confidence goes **up**. If they disagreed, it would
  say so and confidence would go **down**."
- **Recommendations** → priority **high**, concrete actions + monitoring +
  warnings. "It's decision *support*, not agronomic advice — that warning is
  always there."
- **Confidence & limitations** → "Every number is a prototype indicator. It says so."

## 2:10–2:40 — Robustness (pick ONE)

**Option A — kill the network** (Wi-Fi off), press ANALYZE again:
> "Weather source flips to *local dataset*, the run still completes, and the UI
> tells you which source it used. No crash, no fake success."

**Option B — extensibility**, in the spare terminal:
```python
from app.tools.external.adapter import register_external_tool
from app.core.schemas import MaturityStatus
register_external_tool(name="soil_ph", description="interpret soil pH",
    handler=lambda p: {"reading": "acidic" if p["ph"]<6.5 else "ok", "source":"probe"},
    input_fields={"ph": (float, 7.0)}, output_fields={"reading": (str, ...), "source": (str, "")},
    status=MaturityStatus.MOCKED)
```
> "New tool, no core change — the agent now discovers and can call it."

## 2:40–3:00 — Vision

> "Today: a working multimodal agent, offline, zero cost, honestly labelled.
> Next: real IoT sensor streams, then satellite evidence in the same risk
> calculator. Those are interfaces already — not built, not claimed as built."

---

## If something breaks

- Any error on stage → switch to the spare terminal (`make demo`, plain), or set
  `ENVIRONMENT=demo` — the deterministic + precomputed path always completes.
- Do **not** edit thresholds or scoring live.

## Anticipated judge questions → see `docs/judges_faq.md`

Have ready: *why an agent* (it selects/orchestrates tools, visible trace),
*what's real vs mock* (`docs/ai_transparency.md`), *offline* (`pytest -m offline`),
*cost* ($0 demo; real LLM not measured), *add a tool* (the snippet above).

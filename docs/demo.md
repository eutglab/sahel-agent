# Demo script

## One-click path (< 60 s)

1. `make demo` → browser opens the Streamlit app.
2. Sidebar → **Load demo scenario** → *Scenario 4 — Multiple risk factors* → **Load**.
3. **ANALYZE**.
4. Talk through: Agent activity → Situation badge → Risk assessment → Cross-check → Recommendations.

## 3-minute narrated demo

| Time | Say | Show |
|---|---|---|
| **0:00** | "Environmental decisions need an image, sensors, weather, context — usually analysed separately." | title slide / app header |
| **0:30** | "One click loads a realistic situation: a photo, 37 °C, soil moisture 18 %, flowering stage, a location." | Load Demo Scenario, input panel fills |
| **1:00** | "The agent inventories what's available and **chooses** its tools — no fixed pipeline." | press ANALYZE, Agent activity streams |
| **1:30** | "It ran vision, sensor analysis, and weather — then the risk calculator." | trace lines: `Calling analyze_image … done`, etc. |
| **2:00** | "Cross-check: sensor + image + weather **all** point to water stress, so confidence goes up." | Risk assessment → Cross-check: converging evidence |
| **2:30** | "Output is a prioritised recommendation with monitoring steps, warnings, confidence and limitations — decision *support*, not advice." | Recommendations + Confidence & limitations tabs |
| **3:00** | "And it's a platform: I can add a tool at runtime and the agent uses it. It also runs fully offline." | (optional) `register_external_tool` snippet / toggle Wi-Fi |

## Resilience beat (optional, high impact)

- Disconnect the network before/at ANALYZE. The weather source line switches to
  `local dataset` (or `demo`), the run still completes, and the UI *says* which
  source it used. Nothing crashes.
- Or set `LLM_PROVIDER=anthropic` with a bad key: the agent falls back to the
  deterministic planner and the trace says `rule-based planner`.

## Scenarios available

| id | Point |
|---|---|
| `normal` | baseline, low risk, all tools run |
| `water_stress` | dry soil dominates |
| `heat_stress` | high temperature at a sensitive stage |
| `multiple_risks` | **primary** — converging evidence, high combined risk |
| `incomplete_data` | no image, no location → agent skips tools, lowers confidence |

## Reset

Sidebar → **Reset** clears the loaded scenario and last result.

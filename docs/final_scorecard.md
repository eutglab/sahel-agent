# Honest technical scorecard

Scored after an aggressive red-team pass (see `docs/top_10_risks.md`). Scores are
this project's self-assessment against hackathon expectations, not an external
audit.

| Dimension | Score /10 | Evidence | Weakness | Action taken |
|---|--:|---|---|---|
| **Agentic behaviour** | 8 | Perceives modalities, selects tools dynamically (L1 LLM loop with re-ask, L2 rule planner), skips tools for absent modalities, backbone always runs. `tests/test_agent.py`, `tests/test_adversarial.py` | Default demo path is rule-based (L2), not LLM — because the demo runs keyless | L1 loop is real and covered by a test with a fake LLM; documented plainly in `ai_transparency.md` |
| **Tool calling** | 8 | `BaseTool.execute` runs a provider fallback chain, records provider + source note; LLM tool calls validated against the registry; invalid names dropped | LLM could still under-select | Added rule-based fallback when the LLM picks no valid tool (`fix(agent)`) |
| **Multimodality** | 8 | `calculate_risk` consumes the merged bundle; converging evidence raises confidence, diverging lowers it and forces a "provisional" finding | Fusion is heuristic weighting, not learned | Cross-check hardened: no phantom sensor references; contradiction always cuts confidence |
| **Reliability** | 9 | 3-level fallback; every tool has a terminal provider; malformed output / provider crash / invalid tool call all handled; 74 tests, `pytest -m offline` green | — | Regression tests added for each failure mode |
| **Offline capability** | 9 | `pytest -m offline` blocks all sockets and runs all 5 scenarios; `WEATHER_PROVIDER=open_meteo` self-skips offline | Real weather/vision/LLM obviously need network | By design; clearly labelled |
| **UX** | 7 | Streamlit: sidebar runtime status, one-click scenario load, live trace, 6 result tabs, Run details, `DEMO_JUDGE_MODE` one-button setup | Streamlit styling is clean but not bespoke; some agronomy jargon remains | Added input bounds, "insufficient evidence" situation line, sensor-vs-combined-risk caption, judge mode |
| **Innovation** | 7 | Live `register_external_tool`; honesty taxonomy in the UI; resilience as design; fusion that changes the output | Concepts are well-executed rather than novel research | Made all six innovation points demonstrable (`docs/innovation.md`) |
| **Security** | 7 | No secrets in git; `.env` ignored; log scrubbing; image magic-byte + size checks; Pydantic validation; scenario_id path-traversal closed | Single-user local app; no auth/rate-limit (out of scope) | Path traversal fixed + test; label sanitised; documented in `SECURITY.md` |
| **Documentation** | 9 | 20 docs, consistent test counts, `ai_transparency.md`, `build_status.md`, judge FAQ (22 Q), 4 pitch lengths, demo scripts | Volume is large to navigate | README links everything; `final_demo_script.md` is the single stage reference |
| **Hackathon readiness** | 8 | `healthcheck.py` READY, `test_integrations.py` PASS, playbook + day-zero checklist, provider skeletons, `DEMO_JUDGE_MODE` | Real-provider path unverified without a key (can't be, honestly) | `test_integrations.py` verifies mock mode; recipes in `HACKATHON_INTEGRATION.md` |

**Weighted overall: ~80/100.** See `README.md` §"Why Agentic AI?" and the final report for the reasoning.

## Measured performance (this machine, mock LLM, offline)

| Metric | Value |
|---|---|
| Python import (cold) | ~0.35 s |
| First agent run (cold caches) | ~0.15 s |
| Warm agent run | ~7–18 ms (mean ~11 ms, n=20) |
| Benchmark, 5 scenarios | 5/5 success, 10–42 ms each, completeness 1.00 |
| Streamlit import | ~0.4 s |
| Test suite | 74 passed in ~0.8 s |

Real-provider (LLM / live weather) latency and cost: **not measured** — needs a key.

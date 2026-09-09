# Top risks (post red-team)

P0 = would break the demo or the honesty story · P1 = important · P2 = polish.

| # | Prio | Risk | Impact | Likelihood | Mitigation | Status |
|---|---|---|---|---|---|---|
| 1 | P1 | Cross-check referenced "sensor readings" when no sensors were supplied (scenario A) | Judge catches the agent asserting data it doesn't have | Was: certain on image-only inputs | Cross-check now requires the modality to exist before commenting on it | **Fixed** — `test_A_image_only...` |
| 2 | P1 | Zero observation evidence reported combined risk = "low" (reassuring) | "All clear" shown for a no-input analysis | Was: certain on empty input | No-evidence path returns `unknown` + "Insufficient evidence to estimate risk" + confidence 0.1 | **Fixed** — `test_E_no_data_at_all...` |
| 3 | P1 | Contradictory evidence didn't lower confidence (converging +0.1 cancelled diverging −0.1) | Agent looks certain about a contradiction | Was: certain when both fire | Diverging evidence now caps confidence (≤ base − 0.15, ≤ 0.55); recommendation states "sources do not fully converge, confirm on site" | **Fixed** — `test_D_contradiction...` |
| 4 | P1 | LLM picking only invalid/garbage tool names → agent ran **zero** observation tools despite available data | Weak/empty analysis on the real-LLM path | Medium with a real model | Rule-based fallback selection kicks in when the LLM yields no valid tool | **Fixed** — `fix(agent)` commit |
| 5 | P1 | Physically impossible sensor values (temp −100 °C, rainfall 999999 mm) analysed as real | Nonsense drives the risk score | Low (needs bad input) but embarrassing | Plausibility windows in `thresholds.yaml`; out-of-range values flagged as anomalies and dropped from scoring | **Fixed** — `test_F_impossible_values...` |
| 6 | P2 | Path traversal via `scenario_id` in the precomputed loader | Read an arbitrary `*.json` outside `demo_data/precomputed/` | Very low (local single-user tool) | `scenario_id` sanitised to `[A-Za-z0-9_-]`, parent-dir asserted | **Fixed** — `test_scenario_id_path_traversal...` |
| 7 | P2 | Converging-evidence text fired even when the water sub-score was only "low" | Oversells a weak signal | Medium | Gated on water sub-score ≥ moderate band | **Fixed** |
| 8 | P2 | `analyze_sensor_data.risk_level` and `calculate_risk.combined_risk.level` can differ, confusing a viewer | Judge asks "which number is right?" | Medium | UI caption explains they are a single-tool view vs the weighted multimodal view; both are shown | **Fixed (clarified)** |
| 9 | P1 | Real-provider paths (LLM, live weather, vision) cannot be verified without a key/network | Can't prove L1 end-to-end on stage without setup | Certain in a keyless demo | L1 loop proven by a test with a fake LLM; `HACKATHON_INTEGRATION.md` recipes; `test_integrations.py` pre-flight; `DEMO_JUDGE_MODE` for a zero-setup fallback demo | **Accepted + documented** |
| 10 | P2 | Streamlit is functional but visually generic; agronomy jargon in some result text | "School project" first impression | Low–medium | Cleaner layout, badges, `DEMO_JUDGE_MODE`, "decision support not advice" framing; deeper visual polish is out of scope for the time budget | **Partially addressed** |

## Residual risks accepted (not fixed, by design)

- No auth / rate-limiting / multi-tenant isolation — single-user local app.
- Risk heuristic is not agronomically validated — labelled everywhere as a prototype.
- Mock LLM is not a language model — labelled everywhere as `MOCKED`.
- FUTURE interfaces (satellite, IoT pull, voice) are signatures only — they raise `NotIntegratedError`.

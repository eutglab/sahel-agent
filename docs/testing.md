# Testing strategy

```bash
make test            # pytest -m "not integration"   → 61 tests, ~0.5 s
pytest -m offline    # offline guarantee subset (sockets blocked)
pytest               # everything; integration tests self-skip if unconfigured
```

## Layers

| File | Covers |
|---|---|
| `test_sensors.py` | threshold rules, growth-stage escalation, missing-field reporting, tool contract, invalid input → `ToolInputError` |
| `test_risk.py` | low/high bands, multi-factor → high, cross-check converging **and** diverging, confidence scales with modality count, scores bounded [0,1] |
| `test_weather.py` | mock determinism, offline fallback to `local`/`mock`, terminal provider guarantee, unknown location still succeeds |
| `test_recommendation.py` | high-priority actions present, always-present warning + limitations, unknown risk → low priority, tool contract |
| `test_registry.py` | core tools registered, **every** tool satisfies `BaseTool`, `describe_for_llm` hides INTEGRATION_READY stubs, runtime register/unregister, missing tool raises |
| `test_agent.py` | full pipeline on `multiple_risks` (→ high), skips weather/vision when absent, planner is modality-driven, trace populated, **L3 precomputed fallback** on reasoning failure, deterministic fallback without a scenario |
| `test_external_adapter.py` | `register_external_tool` discoverable + callable + in `describe_for_llm`, handler exception captured not raised |
| `test_security.py` | image magic-byte sniff, size cap, unknown-format reject, secret scrubbing, text sanitisation |
| `test_adversarial.py` | red-team scenarios A–F: no fabricated modalities, contradiction detection + confidence drop, implausible-value rejection, no-evidence→unknown, scenario\_id path-traversal |
| `test_offline.py` *(marker: `offline`)* | all 5 demo scenarios run with **every socket blocked**; weather uses local/mock; LLM client is mock; `healthcheck.main()` exits 0 offline |

## Offline guarantee

`tests/conftest.py::block_network` monkeypatches `socket.socket` and
`socket.create_connection` to raise on any connect. `test_offline.py` runs the
whole agent under that fixture — if anything tried to touch the network, the suite
fails.

## What is deliberately not tested

- Real Anthropic/OpenAI/hackathon calls (would need keys + network; those paths
  are `integration`-marked and skipped by default).
- Streamlit rendering beyond a smoke `AppTest` run (manual demo check covers UX).

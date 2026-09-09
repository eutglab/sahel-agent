# Roadmap

All phases past Phase 1 are **future work**. Nothing below Phase 1 is implemented;
the interfaces named exist as stubs that raise `NotIntegratedError`.

## Phase 1 — Multimodal agent MVP  *(this repo)*

Agent loop · tool registry · provider abstraction · vision / sensors / weather /
risk / recommendation · agent trace · 3-level fallback · offline demo · tests ·
docs · hackathon connector layer.

## Phase 2 — Real-time IoT

- Implement `get_sensor_data(device_id)` against an MQTT/HTTP broker.
- Streaming ingestion; rolling-window sensor analysis.
- Alerting via `send_notification` (real channel adapter).

## Phase 3 — Satellite & geospatial

- `get_satellite_data` (e.g. NDVI tiles) and `analyze_location` (soil/terrain
  context) providers.
- Fuse remote-sensing indices into `calculate_risk` as additional evidence.

## Phase 4 — Voice agent

- `speech_to_text` / `text_to_speech` providers.
- Field-friendly voice interaction over low bandwidth.

## Phase 5 — Edge AI

- On-device small model as an L1.5 reasoning fallback between LLM and planner.
- Local caching of provider results; low-bandwidth sync.

## Phase 6 — Autonomous environmental agents

- Scheduled, unattended runs per plot; trend detection; escalation policies.

## Phase 7 — Physical AI / robotics

```
Agent → decision → actuation interface → robot/irrigation controller → environment → observations → Agent
```

- The agent gains an `act` capability behind a hard safety gate.
- Strictly a long-term vision; not designed or prototyped here.

## Low-resource design commitments (carried through every phase)

Lightweight monolith · local fallback for every capability · cloud optional ·
modular tools · offline-first defaults · deployable on modest hardware.

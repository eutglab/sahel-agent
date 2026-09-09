# Pitch

## 30 seconds

> Environmental decisions depend on scattered signals — a photo, sensor readings,
> weather, context — usually looked at separately. **SAHEL Agent** is a multimodal
> AI agent that observes all of them, **decides which specialised tools to use**,
> runs them, cross-checks the results, and produces one prioritised, explainable
> recommendation. It runs fully offline, at zero cost, and you can watch every
> tool it chooses.

## 60 seconds

> In agriculture and environmental monitoring, the data you need to act is
> fragmented across an image, a sensor feed, a weather source and field context.
>
> SAHEL Agent is not a chatbot — it's an agent. Give it whatever you have. It
> inventories the modalities, **selects tools from a registry it can inspect**
> (no fixed pipeline), and runs them through a provider abstraction with a
> fallback chain: real API, then local data, then synthetic — so the demo works
> even with the Wi-Fi off. It fuses the outputs: when the image, the sensors and
> the forecast all point the same way, the risk score and confidence go up, and
> the recommendation cites that converging evidence.
>
> Every capability is tagged IMPLEMENTED, MOCKED, INTEGRATION_READY or FUTURE —
> we don't fake features. And it's a platform: I can register a new tool at
> runtime and the agent starts using it. Zero cost, no key, 41 passing tests.

## 3 minutes

1. **Problem (30s).** Fragmented environmental information; tools used in
   isolation; decisions made with partial pictures.
2. **Solution (30s).** A single well-designed agent:
   `OBSERVE → REASON → USE TOOLS → CROSS-CHECK → RECOMMEND`. Tool registry +
   provider adapters + 3-level fallback.
3. **Live demo (90s).** Load *Multiple risk factors* → ANALYZE → narrate the
   Agent activity trace → open Risk assessment → Cross-check (converging
   evidence) → Recommendations + Confidence & limitations.
4. **Difference (20s).** It selects and orchestrates tools and shows its work;
   it degrades gracefully; it's honest about what's real.
5. **Vision (10s).** Roadmap to IoT, satellite, voice, edge — all as interfaces
   today, none claimed as built.

## 5 minutes (adds to the 3-minute version)

- **Architecture walk (60s).** Show `docs/architecture.md` component map: the
  agent only talks to the registry; tools talk to providers; providers wrap
  services. `LLM_PROVIDER=mock` by default → `$0`, offline.
- **Extensibility beat (45s).** In a Python shell, `register_external_tool(...)`
  a fake search tool; re-run; the agent discovers and calls it. No core change.
- **Resilience beat (30s).** Kill the network mid-demo (or use a bad LLM key);
  the weather source line flips to `local dataset`, the trace says
  `rule-based planner`, the run still completes.
- **Honesty (15s).** Point at the status tags in the UI / `docs/limitations.md`.
- **What's next (15s).** Phase 2: real IoT pull + streaming sensor analysis +
  real alert channel.

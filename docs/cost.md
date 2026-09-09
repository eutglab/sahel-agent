# Cost

## MVP, local / demo

| Item | Cost |
|---|---|
| Python + all dependencies | $0 |
| SQLite run history | $0 |
| Streamlit UI (local) | $0 |
| Weather in demo mode (local dataset / synthetic) | $0 |
| Mock LLM (deterministic, offline) | $0 |
| **Full demo, end to end** | **$0, no API key, no network** |

## Optional real providers

| Item | Cost |
|---|---|
| Weather via **Open-Meteo** (`WEATHER_PROVIDER=open_meteo`) | $0 — free, no key, fair-use limits |
| LLM reasoning + `analyze_image` + `llm` recommendation | pay-per-use under **your** API key and the provider's pricing |
| Hosting (optional, e.g. Streamlit Community Cloud) | free tier available |

### Per-run LLM cost — not measured yet

One full analysis with a real LLM provider is roughly: one system prompt + one
context message (~1–2k tokens), optionally one image, and one grounded synthesis
call (~1–3k tokens in, <1k out). Actual cost depends entirely on the chosen model
and current provider pricing. **We do not quote a number we have not measured.**
Run `benchmark/run_benchmark.py` with a real provider configured to measure it.

## Production

To be determined after a real-provider benchmark: model choice, request volume,
caching hit rate, and hosting all dominate. No production cost figure is claimed
here.

## Cost-control features

- `DEMO_MODE` / `LLM_PROVIDER=mock` → zero external calls.
- Real providers **self-skip** in offline mode (no accidental spend).
- Deterministic `template` recommendation is the default, not the LLM.
- LLM factory caches one client per provider; the agent loop is bounded by
  `AGENT_MAX_ITERATIONS`.

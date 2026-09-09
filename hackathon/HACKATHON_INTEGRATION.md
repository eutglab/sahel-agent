# Hackathon integration guide

**Principle: BUILD ONCE. CONNECT LATER.** The app is complete. On the day you
*connect providers behind interfaces that already exist* — you do not rebuild.

---

## What we expect to receive from organisers

One or more of:

| Thing given | Where it plugs in |
|---|---|
| An LLM API key (Anthropic / OpenAI) | `LLM_PROVIDER` + key in `.env` |
| An OpenAI-compatible LLM endpoint (base URL + key + model) | `LLM_PROVIDER=hackathon` + `HACKATHON_LLM_*` |
| A weather API (base URL + key) | `app/tools/weather/providers/hackathon.py` + `HACKATHON_WEATHER_*` |
| A vision/inference API | `app/tools/vision/providers/hackathon.py` |
| A search / knowledge API | `register_external_tool(...)` or `WEB_SEARCH_*` |
| Any other REST tool | `register_external_tool(...)` |

---

## Connect anything in under 10 minutes

```
1. Obtain credential           -> copy into project-root .env (from credential_template.env)
2. Add environment variable    -> <CAP>_PROVIDER=hackathon  (+ base URL / key vars)
3. Configure provider          -> fill the hackathon.py skeleton, map response -> output schema
                                  OR: register_external_tool(name, description, handler, fields)
4. Register / enable tool      -> TOOL_<NAME>_ENABLED=true   (only for optional tools)
5. Run health check            -> python healthcheck.py
6. Run integration test        -> python scripts/test_integrations.py
7. Enable / switch mode        -> ENVIRONMENT=hackathon ; relaunch the demo
```

If step 5 or 6 fails: set `ENVIRONMENT=demo` and present on the offline path. The
demo is never blocked by an integration.

---

### Recipe A — LLM key (Anthropic)

```bash
# .env
ENVIRONMENT=hackathon
DEMO_MODE=false
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-haiku-4-5
```
```bash
pip install anthropic          # SDK is not bundled
python healthcheck.py           # llm:anthropic -> READY
python scripts/test_integrations.py
```
Now the agent uses **L1 LLM tool-calling**; the trace shows `provider: anthropic`.

### Recipe B — OpenAI-compatible hackathon LLM

```bash
# .env
LLM_PROVIDER=hackathon
HACKATHON_LLM_BASE_URL=https://api.organiser.example/v1
HACKATHON_LLM_API_KEY=...
HACKATHON_LLM_MODEL=their-model-name
```
```bash
pip install openai
python scripts/test_integrations.py
```
If their API is **not** OpenAI-compatible, subclass `HackathonLLMClient` and
override `complete`, `complete_with_tools`, `analyze_image`.

### Recipe C — Weather API

1. Edit `app/tools/weather/providers/hackathon.py`:
   - adjust the request in `run()` (URL params / headers),
   - map their JSON to `WeatherOutput` in `_map_response()`.
2. `.env`:
   ```
   HACKATHON_WEATHER_BASE_URL=...
   HACKATHON_WEATHER_API_KEY=...
   WEATHER_FALLBACK_CHAIN=hackathon,open_meteo,local,mock
   ```
3. `python scripts/test_integrations.py` → `[get_weather] ... hackathon ... OK`.

### Recipe D — Any REST tool (fastest)

```python
# hackathon/adapters/my_tool.py  (import this once at startup, or paste in a shell)
import requests
from app.core.schemas import MaturityStatus
from app.tools.external.adapter import register_external_tool

def handler(payload: dict) -> dict:
    r = requests.get("https://api.organiser.example/x", params=payload, timeout=10)
    r.raise_for_status()
    d = r.json()
    return {"value": d["value"], "source": "organiser-x"}

register_external_tool(
    name="organiser_x",
    description="What the organiser's X service does",
    handler=handler,
    input_fields={"query": (str, ...)},
    output_fields={"value": (float, 0.0), "source": (str, "")},
    status=MaturityStatus.MOCKED,   # so the L1 agent may call it
)
```

Then `registry.get("organiser_x")` works and the agent can call it.

---

## Verifying an integration

`python scripts/test_integrations.py` reports, per tool/provider:
`schema OK`, provider health (`READY` / `NOT CONFIGURED`), `fallback ready`,
and a canned `smoke run` where safe. `NOT CONFIGURED` is informational, never a
hard failure. A non-zero exit means a **core** tool has no working provider.

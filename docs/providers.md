# Provider abstraction

## The rule

> The agent never couples to an external provider.

```
Agent → Tool (BaseTool) → Provider (BaseProvider) → external service / SDK
```

A tool holds an **ordered list of providers** (its fallback chain). `execute()`
tries them in order and records which one answered.

## Selecting providers

Per capability, via `.env`:

| Capability | Primary var | Chain var | Values |
|---|---|---|---|
| LLM | `LLM_PROVIDER` | — (factory) | `mock` · `anthropic` · `openai` · `hackathon` |
| Weather | `WEATHER_PROVIDER` | `WEATHER_FALLBACK_CHAIN` | `open_meteo` · `local` · `mock` · `hackathon` |
| Vision | `VISION_PROVIDER` | `VISION_FALLBACK_CHAIN` | `llm_vision` · `local_heuristic` · `mock` · `hackathon` |
| Recommendation | `RECOMMENDATION_PROVIDER` | `RECOMMENDATION_FALLBACK_CHAIN` | `template` · `llm` · `hackathon` |

The tool builder puts the primary first, then appends the chain entries, then
guarantees a terminal `IMPLEMENTED`/`MOCKED` provider even if you forgot one.

## `BaseProvider` contract

```python
name: str
status: MaturityStatus
requires_credentials: bool
run(payload: BaseModel) -> dict      # raise ProviderError / ProviderUnavailable / NotIntegratedError to fall through
health_check() -> HealthStatus
```

## Provider maturity per tool

| Tool | Provider | Status | Network | Key |
|---|---|---|---|---|
| weather | `open_meteo` | IMPLEMENTED | yes | no |
| weather | `local` | IMPLEMENTED | no | no |
| weather | `mock` | MOCKED | no | no |
| weather | `hackathon` | INTEGRATION_READY | yes | yes |
| vision | `local_heuristic` | IMPLEMENTED | no | no |
| vision | `mock` | MOCKED | no | no |
| vision | `llm_vision` | INTEGRATION_READY | yes | yes |
| vision | `hackathon` | INTEGRATION_READY | yes | yes |
| sensors | `rules` | IMPLEMENTED | no | no |
| risk | `heuristic` | IMPLEMENTED | no | no |
| recommendation | `template` | IMPLEMENTED | no | no |
| recommendation | `llm` | INTEGRATION_READY | yes | yes |
| recommendation | `hackathon` | INTEGRATION_READY | yes | yes |

## LLM abstraction

`app/llm/base.py` defines `LLMClient` with `complete`, `complete_with_tools`
(returns `ToolInvocation[]`), `analyze_image`, `health_check`.
`app/llm/factory.get_llm_client()` **never raises** — an unknown or broken
provider falls back to `MockLLMClient`, so the agent always has a reasoning path.

- `MockLLMClient` (MOCKED): reads `AVAILABLE MODALITIES` from the prompt, returns
  a deterministic tool plan, then a templated summary once results are supplied.
  Zero cost, zero network. Honestly labelled everywhere.
- `AnthropicLLMClient` / `OpenAILLMClient` (INTEGRATION_READY): active only with a
  key **and** the SDK installed (SDKs are commented out of `requirements.txt`).
- `HackathonLLMClient`: subclass of the OpenAI client pointed at
  `HACKATHON_LLM_BASE_URL` (assumed OpenAI-compatible); override 3 methods if not.

## Adding a hackathon provider

1. Fill the skeleton in `app/tools/<cap>/providers/hackathon.py` (weather + vision
   have one; recommendation too).
2. Map the organiser's response to the tool's output schema in `_map_response`.
3. Put credentials in `.env`.
4. Add `hackathon` to the relevant `*_FALLBACK_CHAIN` **or** set `*_PROVIDER=hackathon`.
5. `python scripts/test_integrations.py`.

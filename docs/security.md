# Security (detail)

See [`../SECURITY.md`](../SECURITY.md) for the summary. This file adds detail for
reviewers.

## Secret handling

- `app/core/config.py` loads `.env` with a minimal parser (no `os.system`, no
  interpolation). Real environment variables take precedence over the file.
- `get_secret(name)` is the only sanctioned way to read a credential.
- `_SECRET_KEYS` enumerates the sensitive variable names; `redact()` and
  `public_summary()` guarantee values never appear in the UI or logs.
- `app/core/logging.py` attaches `_ScrubFilter` to the stream handler and passes
  every persisted string through `scrub_secrets()`.
- `RunLogger` stores tool names, provider names, timings, trace lines and
  scrubbed error strings — **not** raw sensor values or images.

## Upload path

`app/core/security.py`:

- `validate_image_upload`: non-empty, `<= MAX_UPLOAD_MB`, magic bytes ∈
  {JPEG, PNG, GIF, WebP}.
- `load_image_safe`: `PIL.Image.verify()` to reject truncated/corrupt files, then
  re-open and convert to RGB.
- On any failure → `ToolInputError`; the agent proceeds without the vision step
  and records the reason in the trace.

## Failure isolation

- `BaseTool.execute` catches `NotIntegratedError`, `ProviderError`,
  `ToolOutputError` and any unexpected `Exception` per provider, moving to the
  next one; the loop cannot be killed by a single provider.
- `SahelAgent.analyze` wraps the reasoning path; on exception it goes to L3
  precomputed, then to the deterministic planner, then returns a `degraded`
  result — it does not raise to the UI.
- `get_llm_client` never raises; worst case is the mock client.

## Dependency surface

`streamlit, pydantic, pyyaml, pillow, numpy, pandas, requests` + `pytest`. LLM
SDKs (`anthropic`, `openai`) are intentionally **not** installed by default.
Only outbound host in normal operation: `api.open-meteo.com` (only when
`WEATHER_PROVIDER=open_meteo` and not offline).

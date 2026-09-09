# Privacy (detail)

See [`../PRIVACY.md`](../PRIVACY.md) for the summary.

## Lifecycle of an uploaded image

1. Streamlit hands the bytes to the app in memory.
2. `validate_image_upload` checks format + size.
3. `analyze_image` providers read the bytes:
   - `local_heuristic` / `mock`: processed locally, never sent anywhere.
   - `llm_vision` (only if a real LLM provider is active and not offline): bytes
     are base64-encoded and sent to that provider under your key.
4. After the run, the bytes are dropped. They are **not** written to disk by the
   app and **not** included in the run log.

## Lifecycle of sensor / location inputs

- Used for the analysis.
- The run log records: tools used, provider per tool, timing, trace lines,
  scrubbed errors, scenario id. It does **not** record the raw temperature /
  moisture / coordinate values.
- `WEATHER_PROVIDER=open_meteo` sends latitude/longitude to Open-Meteo (no
  account, no key).

## Retention & deletion

- `logs/runs.jsonl` and `data/runs.sqlite3` persist until you remove them.
- `make clean` deletes both plus caches.

## Guidance

- Keep `DEMO_MODE=true` for public demos.
- Never upload images of people, faces, plates or documents.
- Treat any real field data as sensitive; prefer synthetic data on stage.

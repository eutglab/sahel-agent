# Privacy

## Data used

- **Demo mode (default):** entirely synthetic. Fictional locations, procedurally
  generated images, hand-authored sensor values. No real persons, farms, or
  organisations.
- **Your own inputs:** whatever you type into the form or upload.

## Data stored

| Item | Stored? | Where | Retention |
|---|---|---|---|
| Uploaded image bytes | **No** | held in memory for the single analysis only | discarded when the run ends |
| Sensor values / location text | Partially | `data/runs.sqlite3` + `logs/runs.jsonl` keep a run *summary* (tools used, providers, timing, trace lines, errors) — **not** the raw form values | until you delete the files (`make clean`) |
| Trace + provider map | Yes (summary form) | same run log | same |

The run log is local to your machine. Nothing is uploaded anywhere by the app
itself.

## Data sent to external services

- **Demo mode:** nothing leaves the machine.
- **`WEATHER_PROVIDER=open_meteo`:** latitude/longitude are sent to
  `api.open-meteo.com` (no key, no account).
- **`LLM_PROVIDER=anthropic|openai|hackathon`:** the assembled text context and,
  for `analyze_image`, the image bytes are sent to that provider under your own
  API key and their terms. The recommendation LLM provider receives only
  *structured tool outputs*, not raw uploads.

## Recommendations

- Keep `DEMO_MODE=true` for demos.
- Do not upload photos containing people, faces, licence plates, or documents.
- Run `make clean` to wipe the local run history.

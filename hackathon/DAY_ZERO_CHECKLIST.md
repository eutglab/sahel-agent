# Day-Zero checklist

Exact commands. Run top to bottom on the hackathon machine.

```bash
# 1. Get the code
git pull

# 2. Environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Demo assets (idempotent)
python scripts/seed_demo.py

# 4. Baseline — must be green BEFORE touching credentials
pytest -m "not integration"          # expect: 41 passed
python healthcheck.py                # expect: STATUS: READY
python benchmark/run_benchmark.py    # expect: all_success true

# 5. Sanity-run the offline demo
streamlit run ui/streamlit_app.py    # load "Multiple risk factors", ANALYZE, Ctrl+C

# --- organisers reveal tools / APIs / credentials ---

# 6. Configure
cp hackathon/credential_template.env .env
$EDITOR .env                         # paste keys / URLs; set ENVIRONMENT=hackathon

# 7. Wire providers (see hackathon/HACKATHON_INTEGRATION.md recipes)
#    - LLM: pip install anthropic  (or openai)
#    - weather/vision: fill app/tools/<cap>/providers/hackathon.py
#    - other REST tools: hackathon/adapters/*.py + register_external_tool()

# 8. Verify integrations
python healthcheck.py
python scripts/test_integrations.py   # NOT CONFIGURED is OK; hard failures are not

# 9. Pick the final scenario, rehearse once
streamlit run ui/streamlit_app.py

# 10. Freeze
git add -A && git commit -m "hackathon: connect <providers>" && git tag stable-demo
#     keep a terminal ready with:  ENVIRONMENT=demo streamlit run ui/streamlit_app.py
```

## If anything is red at step 8

```bash
# fall back to the guaranteed-working offline path
export ENVIRONMENT=demo
streamlit run ui/streamlit_app.py
```
The offline demo shows the full agent behaviour (deterministic planner + local
providers + precomputed fallback). You lose only the "real provider" talking point.

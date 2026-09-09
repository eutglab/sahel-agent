# Hackathon-day playbook

Assumes the schedule: doors + tool reveal ~15 min in, presentation later.

| When | Action | Success check |
|---|---|---|
| **T-60** | `git pull`; `make setup`; `pytest -m "not integration"`; `python healthcheck.py` | 41 passed · STATUS: READY |
| **T-55** | Run the offline demo once (`make demo`), load *Multiple risk factors*, ANALYZE | full result in < 15 s |
| **T-45** | Organisers reveal APIs/keys. `cp hackathon/credential_template.env .env`; paste values; `ENVIRONMENT=hackathon` | `.env` populated, not committed |
| **T-35** | Wire providers: `pip install anthropic`/`openai`; fill `hackathon.py` skeletons or `hackathon/adapters/*.py` + `register_external_tool` | code compiles |
| **T-20** | `python healthcheck.py`; `python scripts/test_integrations.py` | no **hard** failures; real providers `READY` |
| **T-15** | Rehearse the 3-minute demo end to end with real providers | trace shows `provider: <real>` |
| **T-10** | Rehearse the resilience beat: pull network → run → confirm graceful fallback | source line flips, run completes |
| **T-5** | `git commit`; `git tag stable-demo`. Open a spare terminal with `ENVIRONMENT=demo` ready | tag exists; fallback terminal ready |
| **Present** | Load *Multiple risk factors* → ANALYZE → narrate Agent activity → Cross-check → Recommendation → (optional) add a tool live → (optional) kill network | audience sees tool selection + fusion + resilience |
| **Post** | Keep iterating on branches; never force-push `stable-demo` | — |

## Roles (if 2+ people)

- **Driver:** runs the laptop, executes the demo, never edits code during the pitch.
- **Integrator:** owns `.env` + provider skeletons + `test_integrations.py`.
- **Narrator:** speaks to `docs/pitch.md`; watches the clock.

## Hard rules

1. If `test_integrations.py` has a hard failure at T-20, present on `ENVIRONMENT=demo`.
2. Never paste a key into a file other than `.env`.
3. Never change `thresholds.yaml` or scoring logic during the event to "improve" a
   number — it breaks honesty and the precomputed fallbacks.
4. One person, one `git commit` at T-5. Then hands off the keyboard.

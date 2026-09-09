# Benchmark

```bash
python benchmark/run_benchmark.py          # table
python benchmark/run_benchmark.py --json   # machine-readable
```

Runs the agent over the 5 demo scenarios and measures, **from real runs on the
current machine**:

- reasoning mode
- number of tools used
- wall-clock execution time (ms)
- success (recommendation produced)
- whether a fallback level was used
- output completeness (fraction of required recommendation keys + observation
  sections that are non-empty)

## Latest local run (mock LLM, offline)

| scenario | mode | tools | ms | ok | fallback | completeness |
|---|---|---|---|---|---|---|
| heat_stress | deterministic | 5 | ~32 | ✓ | no | 1.00 |
| incomplete_data | deterministic | 3 | ~7 | ✓ | no | 1.00 |
| multiple_risks | deterministic | 5 | ~17 | ✓ | no | 1.00 |
| normal | deterministic | 5 | ~13 | ✓ | no | 1.00 |
| water_stress | deterministic | 5 | ~11 | ✓ | no | 1.00 |

**Summary:** 5/5 success, mean ~16 ms, max ~32 ms, mean completeness 1.00, 0 fallbacks.

> Numbers vary per machine. Re-run to refresh this table; do not cite it as a
> fixed spec.

## Not measured yet

- Real LLM provider latency and token cost (needs a key + network).
- Open-Meteo round-trip latency under `ENVIRONMENT=real`.
- Accuracy / agronomic validity of the risk heuristic — **out of scope**; this is
  a prototype indicator, see [`limitations.md`](limitations.md).

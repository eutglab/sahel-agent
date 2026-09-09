#!/usr/bin/env python3
"""Local benchmark — measures the agent over the demo scenarios.

Reports, per scenario: reasoning mode, tools used, execution time, success,
whether a fallback was needed, and output completeness. Nothing is fabricated;
values come from real runs on this machine.

Run:  python benchmark/run_benchmark.py [--json]
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agent.agent import SahelAgent  # noqa: E402
from app.core.schemas import AgentInput, Location, SensorReadings  # noqa: E402
from app.data.demo_data import list_scenarios, load_scenario_image  # noqa: E402

_REQUIRED_REC_KEYS = {
    "priority", "main_finding", "recommended_actions",
    "monitoring_actions", "warnings", "confidence", "limitations",
}


def _completeness(result) -> float:
    rec = result.recommendation or {}
    have = sum(1 for k in _REQUIRED_REC_KEYS if rec.get(k) not in (None, "", []))
    obs = result.observation
    sections = [obs.sensors, obs.risk, obs.risk and obs.risk.get("cross_check")]
    have += sum(1 for s in sections if s)
    total = len(_REQUIRED_REC_KEYS) + len(sections)
    return round(have / total, 2)


def run(as_json: bool = False) -> int:
    list_scenarios.cache_clear()
    agent = SahelAgent()
    rows = []
    for scn in list_scenarios():
        img = load_scenario_image(scn)
        ai = AgentInput(
            text_context=scn.get("text_context", ""),
            image_bytes=img,
            image_name=scn.get("image"),
            sensors=SensorReadings(**scn.get("sensors", {})),
            location=Location(**scn.get("location", {})),
            scenario_id=scn["id"],
        )
        t0 = time.time()
        result = agent.analyze(ai)
        elapsed_ms = round((time.time() - t0) * 1000, 1)
        rows.append(
            {
                "scenario": scn["id"],
                "reasoning_mode": result.reasoning_mode,
                "tools_used": result.tools_used,
                "n_tools": len(result.tools_used),
                "execution_ms": elapsed_ms,
                "success": result.recommendation is not None,
                "fallback_used": result.degraded,
                "output_completeness": _completeness(result),
                "errors": result.errors,
            }
        )

    summary = {
        "scenarios": len(rows),
        "all_success": all(r["success"] for r in rows),
        "mean_execution_ms": round(statistics.mean(r["execution_ms"] for r in rows), 1),
        "max_execution_ms": max(r["execution_ms"] for r in rows),
        "mean_completeness": round(statistics.mean(r["output_completeness"] for r in rows), 2),
        "fallbacks": sum(1 for r in rows if r["fallback_used"]),
    }

    if as_json:
        print(json.dumps({"rows": rows, "summary": summary}, indent=2, default=str))
        return 0 if summary["all_success"] else 1

    print("SAHEL AGENT — LOCAL BENCHMARK")
    print("=" * 88)
    print(f"{'scenario':16} {'mode':16} {'tools':6} {'ms':>8} {'ok':>4} {'fallbk':>7} {'complete':>9}")
    print("-" * 88)
    for r in rows:
        print(
            f"{r['scenario']:16} {r['reasoning_mode']:16} {r['n_tools']:6} "
            f"{r['execution_ms']:8.1f} {str(r['success']):>4} {str(r['fallback_used']):>7} "
            f"{r['output_completeness']:9.2f}"
        )
    print("-" * 88)
    print(json.dumps(summary, indent=2))
    print("\nNote: measured on this machine, mock LLM, offline. Real-provider latency not measured yet.")
    return 0 if summary["all_success"] else 1


if __name__ == "__main__":
    raise SystemExit(run(as_json="--json" in sys.argv))

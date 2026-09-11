#!/usr/bin/env python3
"""SAHEL Agent — integration pre-flight check.

For every tool + provider, checks:
  * schema round-trip (input/output models load)
  * provider health (reachable / credential present / configured)
  * a smoke execution with a canned input (where safe / offline)
  * fallback availability (>= 2 providers, or a guaranteed terminal one)

Providers that are INTEGRATION_READY but not configured are reported as
NOT CONFIGURED — informational, never a hard failure.

Run:  python scripts/test_integrations.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.schemas import HealthState, MaturityStatus  # noqa: E402
from app.tools.registry import get_registry  # noqa: E402

CANNED = {
    "analyze_sensor_data": {
        "temperature_c": 34, "soil_moisture_pct": 20, "air_humidity_pct": 40,
        "rainfall_mm": 1, "growth_stage": "flowering",
    },
    "get_weather": {"label": "Fictional Site Alpha", "latitude": 14.5, "longitude": -4.2},
    "calculate_risk": {"sensors": None, "vision": None, "weather": None, "growth_stage": "flowering"},
    "generate_recommendation": {"modalities": [], "growth_stage": "flowering"},
    "search_web": {"query": "heat stress crop management advisory", "max_results": 2},
}


def main() -> int:
    print("SAHEL AGENT — INTEGRATION PRE-FLIGHT")
    print("=" * 60)
    reg = get_registry(refresh=True)
    hard_fail = 0

    for tool in reg.tools():
        print(f"\n[{tool.name}]  status={tool.status.value}")
        # schema round-trip
        try:
            tool.input_schema().model_json_schema()
            tool.output_schema().model_json_schema()
            print("  schema           : OK")
        except Exception as exc:  # noqa: BLE001
            hard_fail += 1
            print(f"  schema           : FAIL ({exc})")
            continue

        # provider health + fallback
        provs = tool.providers()
        print(f"  providers        : {', '.join(p.name for p in provs) or '(none)'}")
        has_terminal = any(
            p.status in {MaturityStatus.IMPLEMENTED, MaturityStatus.MOCKED} for p in provs
        )
        print(f"  fallback ready   : {'yes' if (len(provs) >= 2 or has_terminal) else 'NO'}")
        for p in provs:
            try:
                h = p.health_check()
                state = h.state.value if isinstance(h.state, HealthState) else str(h.state)
            except Exception as exc:  # noqa: BLE001
                state = f"health crashed: {exc}"
            tag = "NOT CONFIGURED" if (
                p.status == MaturityStatus.INTEGRATION_READY and "not " in (getattr(h, "detail", "") or "").lower()
            ) else state
            print(f"    - {p.name:16} {tag}  ({getattr(h, 'detail', '')})")

        # smoke execution
        if tool.name in CANNED:
            t0 = time.time()
            rec = tool.execute(CANNED[tool.name])
            dt = (time.time() - t0) * 1000
            if rec.success:
                print(f"  smoke run        : OK via '{rec.provider_used}' ({dt:.0f} ms)")
            else:
                # Only a hard failure for core tools with no working provider.
                if tool.status == MaturityStatus.IMPLEMENTED:
                    hard_fail += 1
                    print(f"  smoke run        : FAIL ({rec.error})")
                else:
                    print(f"  smoke run        : n/a ({rec.error})")
        else:
            print("  smoke run        : skipped (needs image / prior outputs)")

    print("\n" + "=" * 60)
    print(f"RESULT: {'FAIL' if hard_fail else 'PASS'}   ({hard_fail} hard failures)")
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())

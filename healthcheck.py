#!/usr/bin/env python3
"""SAHEL Agent — health check.

Verifies configuration, the agent, the tool registry, every tool's providers,
and reports optional integrations as informational (never a blocking failure).

Exit code: 0 if READY or WARNING only, 1 if any core component FAILED.
Run:  python healthcheck.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.config import settings  # noqa: E402
from app.core.schemas import HealthState  # noqa: E402

ICON = {HealthState.READY: "✓", HealthState.WARNING: "○", HealthState.FAILED: "✗"}
CORE_TOOLS = {"analyze_image", "analyze_sensor_data", "get_weather", "calculate_risk", "generate_recommendation"}


def main() -> int:
    print("SAHEL AGENT HEALTH CHECK")
    print("=" * 52)
    cfg = settings.public_summary()
    print(f"environment            : {cfg['environment']}")
    print(f"demo_mode              : {cfg['demo_mode']}")
    print(f"llm_provider           : {cfg['llm_provider']}")
    print(f"weather / vision / rec : {cfg['weather_provider']} / {cfg['vision_provider']} / {cfg['recommendation_provider']}")
    print(f"anthropic key          : {cfg['anthropic_key']}")
    print("-" * 52)

    failed = 0
    warned = 0

    # --- config sanity ---------------------------------------------- #
    try:
        assert settings.agent_max_iterations >= 1
        assert settings.tool_timeout_seconds >= 1
        print(f"{ICON[HealthState.READY]} Configuration")
    except AssertionError as exc:
        failed += 1
        print(f"{ICON[HealthState.FAILED]} Configuration — {exc}")

    # --- registry + agent ----------------------------------------- #
    try:
        from app.tools.registry import get_registry

        reg = get_registry(refresh=True)
        print(f"{ICON[HealthState.READY]} Tool Registry — {len(reg.list())} tools: {', '.join(reg.list())}")
    except Exception as exc:  # noqa: BLE001
        failed += 1
        print(f"{ICON[HealthState.FAILED]} Tool Registry — {exc}")
        return 1

    try:
        from app.agent.agent import SahelAgent

        SahelAgent()
        print(f"{ICON[HealthState.READY]} Agent")
    except Exception as exc:  # noqa: BLE001
        failed += 1
        print(f"{ICON[HealthState.FAILED]} Agent — {exc}")

    try:
        from app.llm.factory import get_llm_client

        llm_health = get_llm_client().health_check()
        _print_health(llm_health)
        if llm_health.state == HealthState.WARNING:
            warned += 1
    except Exception as exc:  # noqa: BLE001
        warned += 1
        print(f"{ICON[HealthState.WARNING]} LLM client — {exc}")

    # --- per-tool provider health ------------------------------------ #
    print("-" * 52)
    for h in reg.health_check():
        _print_health(h)
        name = h.component.replace("tool:", "")
        if h.state == HealthState.FAILED:
            if name in CORE_TOOLS:
                failed += 1
            else:
                warned += 1
        elif h.state == HealthState.WARNING:
            warned += 1

    # --- optional integrations (informational only) ---------------- #
    print("-" * 52)
    print("Optional integrations:")
    optional = {
        "web_search": "search_web",
        "file_analysis": "analyze_file",
        "notification": "send_notification",
    }
    for cap, tool_name in optional.items():
        if reg.has(tool_name):
            state = "ENABLED (INTEGRATION_READY — wire a provider)"
        elif settings.tool_enabled(cap):
            state = "enabled but failed to load"
        else:
            state = "available, disabled by config (TOOL_%s_ENABLED=true to activate)" % cap.upper()
        print(f"  ○ {cap} ({tool_name}): {state}")
    for cap in ("geospatial", "satellite", "voice", "iot"):
        print(f"  ○ {cap}: FUTURE — interface documented, not built")

    # --- demo assets ---------------------------------------------- #
    print("-" * 52)
    try:
        from app.data.demo_data import list_scenarios

        list_scenarios.cache_clear()
        n = len(list_scenarios())
        if n >= 1:
            print(f"{ICON[HealthState.READY]} Demo scenarios — {n} available")
        else:
            warned += 1
            print(f"{ICON[HealthState.WARNING]} Demo scenarios — none found (run scripts/seed_demo.py)")
    except Exception as exc:  # noqa: BLE001
        warned += 1
        print(f"{ICON[HealthState.WARNING]} Demo scenarios — {exc}")

    print("=" * 52)
    status = "FAILED" if failed else ("WARNING" if warned else "READY")
    print(f"STATUS: {status}   ({failed} failed, {warned} warnings)")
    return 1 if failed else 0


def _print_health(h) -> None:
    state = h.state if isinstance(h.state, HealthState) else HealthState(h.state)
    label = h.component
    detail = f" — {h.detail}" if h.detail else ""
    print(f"{ICON[state]} {label}{detail}")


if __name__ == "__main__":
    raise SystemExit(main())

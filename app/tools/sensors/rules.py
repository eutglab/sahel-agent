"""Transparent, configurable threshold rules for sensor analysis.

Everything here is deterministic and documented as a PROTOTYPE heuristic.
Thresholds come from ``app/data/thresholds.yaml`` and are reloaded per call.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml

from app.core.config import PROJECT_ROOT
from app.tools.sensors.schema import SensorIndicator, SensorInput, SensorOutput

_THRESHOLDS_PATH = PROJECT_ROOT / "app" / "data" / "thresholds.yaml"


@lru_cache(maxsize=1)
def _load_thresholds_cached(mtime: float) -> Dict[str, Any]:  # noqa: ARG001 - mtime busts cache
    return yaml.safe_load(_THRESHOLDS_PATH.read_text(encoding="utf-8"))


def load_thresholds() -> Dict[str, Any]:
    mtime = _THRESHOLDS_PATH.stat().st_mtime if _THRESHOLDS_PATH.exists() else 0.0
    return _load_thresholds_cached(mtime)


_LEVEL_ORDER = ["low", "moderate", "elevated", "high"]


def _escalate(current: str, candidate: str) -> str:
    return candidate if _LEVEL_ORDER.index(candidate) > _LEVEL_ORDER.index(current) else current


def analyze(payload: SensorInput) -> Dict[str, Any]:
    th = load_thresholds()
    indicators = []
    anomalies = []
    explanation = []
    missing = []
    level = "low"

    stage = payload.growth_stage.value

    # --- soil moisture ------------------------------------------------- #
    sm = payload.soil_moisture_pct
    if sm is None:
        missing.append("soil_moisture_pct")
    else:
        cfg = th["soil_moisture_pct"]
        sensitive = stage in cfg.get("sensitive_stages", [])
        if sm < cfg["critical_low"]:
            assessment = "critically low"
            anomalies.append(f"soil moisture {sm}% is below critical ({cfg['critical_low']}%)")
            level = _escalate(level, "high" if sensitive else "elevated")
        elif sm < cfg["low"]:
            assessment = "low"
            anomalies.append(f"soil moisture {sm}% is low (<{cfg['low']}%)")
            level = _escalate(level, "elevated" if sensitive else "moderate")
        elif sm > cfg["high"]:
            assessment = "waterlogged risk"
            anomalies.append(f"soil moisture {sm}% is very high (>{cfg['high']}%)")
            level = _escalate(level, "moderate")
        elif cfg["optimal_min"] <= sm <= cfg["optimal_max"]:
            assessment = "optimal"
        else:
            assessment = "acceptable"
        detail = "growth stage is moisture-sensitive" if sensitive else ""
        indicators.append(SensorIndicator(name="soil_moisture_pct", value=sm, assessment=assessment, detail=detail))
        if assessment in {"low", "critically low"}:
            explanation.append(
                f"Low soil moisture at the {stage} stage can restrict water uptake; "
                f"confirm with a field probe before acting."
            )

    # --- temperature ------------------------------------------------- #
    t = payload.temperature_c
    if t is None:
        missing.append("temperature_c")
    else:
        cfg = th["temperature_c"]
        if t >= cfg["severe_heat"]:
            assessment = "severe heat"
            anomalies.append(f"temperature {t}°C at/above severe-heat threshold ({cfg['severe_heat']}°C)")
            level = _escalate(level, "high")
        elif t >= cfg["heat_stress"]:
            assessment = "heat stress"
            anomalies.append(f"temperature {t}°C in heat-stress range (>={cfg['heat_stress']}°C)")
            level = _escalate(level, "elevated")
        elif t <= cfg["cold_stress"]:
            assessment = "cold stress"
            anomalies.append(f"temperature {t}°C in cold-stress range (<={cfg['cold_stress']}°C)")
            level = _escalate(level, "elevated")
        elif cfg["optimal_min"] <= t <= cfg["optimal_max"]:
            assessment = "optimal"
        else:
            assessment = "acceptable"
        indicators.append(SensorIndicator(name="temperature_c", value=t, assessment=assessment))
        if assessment in {"heat stress", "severe heat"}:
            explanation.append(
                f"Air temperature around {t}°C increases evapotranspiration and can compound water stress."
            )

    # --- air humidity ------------------------------------------------- #
    h = payload.air_humidity_pct
    if h is None:
        missing.append("air_humidity_pct")
    else:
        cfg = th["air_humidity_pct"]
        if h < cfg["very_low"]:
            assessment = "very low"
            anomalies.append(f"air humidity {h}% is very low (<{cfg['very_low']}%)")
            level = _escalate(level, "moderate")
        elif h < cfg["low"]:
            assessment = "low"
            level = _escalate(level, "moderate")
        elif h > cfg["high"]:
            assessment = "high (disease-favourable)"
            level = _escalate(level, "moderate")
        elif cfg["optimal_min"] <= h <= cfg["optimal_max"]:
            assessment = "optimal"
        else:
            assessment = "acceptable"
        indicators.append(SensorIndicator(name="air_humidity_pct", value=h, assessment=assessment))
        if assessment in {"very low", "low"}:
            explanation.append(
                f"Low air humidity ({h}%) raises the vapour-pressure deficit and water demand."
            )

    # --- rainfall ------------------------------------------------- #
    r = payload.rainfall_mm
    if r is None:
        missing.append("rainfall_mm")
    else:
        cfg = th["rainfall_mm"]
        if r <= cfg["none"]:
            assessment = "none recorded"
        elif r < cfg["moderate"]:
            assessment = "light"
        elif r < cfg["heavy"]:
            assessment = "moderate"
        else:
            assessment = "heavy"
            anomalies.append(f"rainfall {r} mm is heavy (>= {cfg['heavy']} mm)")
        indicators.append(SensorIndicator(name="rainfall_mm", value=r, assessment=assessment))
        if assessment == "none recorded" and sm is not None and sm < th["soil_moisture_pct"]["low"]:
            explanation.append("No recent rainfall combined with low soil moisture points to developing water stress.")

    if payload.growth_stage != payload.growth_stage.unknown:
        indicators.append(
            SensorIndicator(name="growth_stage", value=None, assessment=stage, detail="context only")
        )
    else:
        missing.append("growth_stage")

    if not explanation:
        explanation.append("Sensor values are within acceptable prototype ranges; no threshold breaches detected.")

    out = SensorOutput(
        risk_level=level,
        indicators=indicators,
        anomalies=anomalies,
        explanation=explanation,
        missing_fields=missing,
    )
    return out.model_dump()

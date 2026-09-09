"""Explainable prototype risk heuristic.

Produces three sub-scores in [0, 1] — water stress, heat stress, environmental —
then a weighted combined score. Every point added to a score carries a named
driver so the UI can show *why*. A cross-check step rewards converging evidence
across modalities (sensors + vision + weather) and flags contradictions.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.tools.sensors.rules import load_thresholds
from app.tools.risk.schema import CrossCheck, RiskInput, RiskOutput, SubScore


def _band(score: float) -> str:
    th = load_thresholds()["risk_bands"]
    if score >= th["high_threshold"]:
        return "high"
    if score >= th["low"]:
        return "moderate"
    return "low"


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, round(x, 3)))


def _indicator(sensors: Dict[str, Any] | None, name: str) -> Dict[str, Any] | None:
    if not sensors:
        return None
    for ind in sensors.get("indicators", []):
        if ind.get("name") == name:
            return ind
    return None


def _water_stress(inp: RiskInput) -> SubScore:
    score = 0.0
    drivers: List[str] = []
    sm = _indicator(inp.sensors, "soil_moisture_pct")
    if sm:
        assessment = sm.get("assessment", "")
        if assessment == "critically low":
            score += 0.6
            drivers.append("soil moisture critically low")
        elif assessment == "low":
            score += 0.35
            drivers.append("soil moisture low")
    rain = _indicator(inp.sensors, "rainfall_mm")
    if rain and rain.get("assessment") == "none recorded":
        score += 0.15
        drivers.append("no recent rainfall recorded")
    hum = _indicator(inp.sensors, "air_humidity_pct")
    if hum and hum.get("assessment") in {"very low", "low"}:
        score += 0.1
        drivers.append("low air humidity raises water demand")
    if inp.growth_stage in {"flowering", "fruiting"} and score > 0:
        score += 0.15
        drivers.append(f"{inp.growth_stage} stage is water-sensitive")

    # Weather: dry forecast compounds water stress.
    if inp.weather:
        rp = inp.weather.get("rain_probability")
        if isinstance(rp, (int, float)) and rp <= 20 and score > 0:
            score += 0.1
            drivers.append(f"forecast rain probability low ({rp}%)")

    # Vision corroboration.
    if inp.vision:
        signs = " ".join(inp.vision.get("possible_signs", [])).lower()
        if any(k in signs for k in ("wilt", "curl", "dry", "water")):
            score += 0.1
            drivers.append("image shows possible water-stress signs")

    return SubScore(name="water_stress", score=_clamp(score), level=_band(_clamp(score)), drivers=drivers)


def _heat_stress(inp: RiskInput) -> SubScore:
    score = 0.0
    drivers: List[str] = []
    t = _indicator(inp.sensors, "temperature_c")
    if t:
        assessment = t.get("assessment", "")
        if assessment == "severe heat":
            score += 0.7
            drivers.append("temperature at/above severe-heat threshold")
        elif assessment == "heat stress":
            score += 0.45
            drivers.append("temperature in heat-stress range")
        elif assessment == "cold stress":
            score += 0.4
            drivers.append("temperature in cold-stress range")
    if inp.weather:
        wt = inp.weather.get("temperature_c")
        if isinstance(wt, (int, float)) and wt >= load_thresholds()["temperature_c"]["heat_stress"]:
            score += 0.15
            drivers.append(f"weather temperature also elevated ({wt}°C)")
    if inp.growth_stage == "flowering" and score > 0:
        score += 0.1
        drivers.append("flowering is heat-sensitive")
    if inp.vision:
        signs = " ".join(inp.vision.get("possible_signs", [])).lower()
        if any(k in signs for k in ("scorch", "burn", "yellow")):
            score += 0.1
            drivers.append("image shows possible heat/scorch signs")
    return SubScore(name="heat_stress", score=_clamp(score), level=_band(_clamp(score)), drivers=drivers)


def _environmental(inp: RiskInput) -> SubScore:
    score = 0.0
    drivers: List[str] = []
    hum = _indicator(inp.sensors, "air_humidity_pct")
    if hum and hum.get("assessment", "").startswith("high"):
        score += 0.3
        drivers.append("high humidity is disease-favourable")
    if hum and hum.get("assessment") == "very low":
        score += 0.2
        drivers.append("very low humidity stresses foliage")
    rain = _indicator(inp.sensors, "rainfall_mm")
    if rain and rain.get("assessment") == "heavy":
        score += 0.3
        drivers.append("heavy rainfall — waterlogging / runoff risk")
    sm = _indicator(inp.sensors, "soil_moisture_pct")
    if sm and sm.get("assessment") == "waterlogged risk":
        score += 0.3
        drivers.append("soil near waterlogging")
    if inp.vision:
        n_signs = len(inp.vision.get("possible_signs", []))
        if n_signs >= 2:
            score += 0.2
            drivers.append(f"image flags {n_signs} possible stress signs")
        elif n_signs == 1:
            score += 0.1
            drivers.append("image flags a possible stress sign")
    return SubScore(name="environmental", score=_clamp(score), level=_band(_clamp(score)), drivers=drivers)


def _cross_check(inp: RiskInput, water: SubScore, heat: SubScore) -> CrossCheck:
    converging: List[str] = []
    diverging: List[str] = []
    adj = 0.0

    has_sensors = inp.sensors is not None
    has_vision = inp.vision is not None
    has_weather = inp.weather is not None

    has_sensor_water = has_sensors and any("soil moisture" in d for d in water.drivers)
    has_vision_water = has_vision and any(
        k in " ".join(inp.vision.get("possible_signs", [])).lower()
        for k in ("wilt", "curl", "dry", "water", "yellow")
    )
    has_weather_dry = (
        has_weather
        and isinstance(inp.weather.get("rain_probability"), (int, float))
        and inp.weather["rain_probability"] <= 20
    )

    # Converging evidence only counts when >= 2 DISTINCT modalities agree AND the
    # water sub-score is at least 'moderate' (don't oversell a 'low' score).
    water_signals = sum([bool(has_sensor_water), bool(has_vision_water), bool(has_weather_dry)])
    if water_signals >= 2 and water.score >= 0.33:
        converging.append(
            "Water-stress signal supported by "
            + " + ".join(
                s for s, ok in [
                    ("sensor readings", has_sensor_water),
                    ("image observations", has_vision_water),
                    ("weather forecast", has_weather_dry),
                ] if ok
            )
        )
        adj += 0.1

    # Contradiction: image and sensors disagree. Only assert something about
    # sensor readings when sensor data actually exists.
    if has_sensors and has_vision:
        img_flags = bool(inp.vision.get("possible_signs"))
        sensors_stressed = water.score > 0.5 or heat.score > 0.5
        sensors_calm = water.score < 0.2 and heat.score < 0.2
        if not img_flags and sensors_stressed:
            diverging.append(
                "Image shows no visible stress signs, but sensor readings indicate elevated risk."
            )
            adj -= 0.15
        if img_flags and sensors_calm:
            diverging.append(
                "Image flags possible stress signs, but sensor readings are within range."
            )
            adj -= 0.12

    return CrossCheck(
        converging_evidence=converging,
        diverging_evidence=diverging,
        confidence_adjustment=round(adj, 3),
    )


def _base_confidence(inp: RiskInput) -> float:
    modalities = sum(bool(x) for x in (inp.sensors, inp.vision, inp.weather))
    return {0: 0.2, 1: 0.4, 2: 0.6, 3: 0.72}[modalities]


def calculate(inp: RiskInput) -> Dict[str, Any]:
    th = load_thresholds()["risk_weights"]
    water = _water_stress(inp)
    heat = _heat_stress(inp)
    env = _environmental(inp)

    n_modalities = sum(bool(x) for x in (inp.sensors, inp.vision, inp.weather))

    # No observation at all -> do not report a reassuring "low"; report "unknown".
    if n_modalities == 0:
        unknown = SubScore(
            name="combined_risk", score=0.0, level="unknown",
            drivers=["no sensor, image or weather evidence was available"],
        )
        return RiskOutput(
            water_stress=water, heat_stress=heat, environmental=env,
            combined_risk=unknown,
            cross_check=CrossCheck(),
            confidence=0.1,
        ).model_dump()

    combined_score = _clamp(
        water.score * th["water_stress"]
        + heat.score * th["heat_stress"]
        + env.score * th["environmental"]
    )
    xc = _cross_check(inp, water, heat)
    combined_score = _clamp(combined_score + max(0.0, xc.confidence_adjustment) * 0.5)

    combined_drivers = []
    for sub in (water, heat, env):
        if sub.score >= 0.33:
            combined_drivers.append(f"{sub.name.replace('_', ' ')}: {sub.level}")
    if not combined_drivers:
        combined_drivers.append("no sub-score reached the 'moderate' band")

    combined = SubScore(
        name="combined_risk",
        score=combined_score,
        level=_band(combined_score),
        drivers=combined_drivers,
    )

    confidence = _base_confidence(inp) + xc.confidence_adjustment
    if xc.diverging_evidence:
        # A genuine contradiction must always lower confidence, even if some
        # other evidence converges. Cap it so the agent cannot look certain.
        confidence = min(confidence, _base_confidence(inp) - 0.15, 0.55)
    confidence = _clamp(confidence)

    return RiskOutput(
        water_stress=water,
        heat_stress=heat,
        environmental=env,
        combined_risk=combined,
        cross_check=xc,
        confidence=confidence,
    ).model_dump()

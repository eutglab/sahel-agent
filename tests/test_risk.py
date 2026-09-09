from __future__ import annotations

from app.tools.risk.rules import calculate
from app.tools.risk.schema import RiskInput
from app.tools.sensors.rules import analyze
from app.tools.sensors.schema import SensorInput


def _sensors(**kw):
    return analyze(SensorInput(**kw))


def test_risk_low_when_all_optimal():
    inp = RiskInput(sensors=_sensors(temperature_c=25, soil_moisture_pct=45, air_humidity_pct=55,
                                     rainfall_mm=5, growth_stage="vegetative"),
                    growth_stage="vegetative")
    out = calculate(inp)
    assert out["combined_risk"]["level"] == "low"


def test_risk_high_on_multiple_factors():
    inp = RiskInput(
        sensors=_sensors(temperature_c=37, soil_moisture_pct=18, air_humidity_pct=31,
                         rainfall_mm=0, growth_stage="flowering"),
        weather={"rain_probability": 8, "temperature_c": 36},
        vision={"possible_signs": ["noticeable yellow/brown discolouration — potential stress"]},
        growth_stage="flowering",
    )
    out = calculate(inp)
    assert out["combined_risk"]["level"] == "high"
    assert out["water_stress"]["score"] > 0.5
    assert out["cross_check"]["converging_evidence"]  # sensors + vision + weather agree


def test_risk_confidence_scales_with_modalities():
    only_sensors = RiskInput(sensors=_sensors(temperature_c=30, soil_moisture_pct=20), growth_stage="flowering")
    all_three = RiskInput(
        sensors=_sensors(temperature_c=30, soil_moisture_pct=20),
        weather={"rain_probability": 10},
        vision={"possible_signs": []},
        growth_stage="flowering",
    )
    assert calculate(all_three)["confidence"] >= calculate(only_sensors)["confidence"]


def test_risk_scores_bounded():
    out = calculate(RiskInput(
        sensors=_sensors(temperature_c=45, soil_moisture_pct=2, air_humidity_pct=5,
                         rainfall_mm=0, growth_stage="flowering"),
        weather={"rain_probability": 0}, vision={"possible_signs": ["a", "b", "c"]},
        growth_stage="flowering",
    ))
    for key in ("water_stress", "heat_stress", "environmental", "combined_risk"):
        assert 0.0 <= out[key]["score"] <= 1.0
    assert 0.0 <= out["confidence"] <= 1.0


def test_risk_diverging_evidence_flagged():
    out = calculate(RiskInput(
        sensors=_sensors(temperature_c=38, soil_moisture_pct=10, growth_stage="flowering"),
        vision={"possible_signs": []},  # image says nothing wrong
        growth_stage="flowering",
    ))
    assert out["cross_check"]["diverging_evidence"]

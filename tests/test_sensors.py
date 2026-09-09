from __future__ import annotations

from app.tools.sensors.rules import analyze
from app.tools.sensors.schema import SensorInput
from app.tools.sensors.tool import build


def test_sensor_optimal_is_low_risk():
    out = analyze(SensorInput(temperature_c=25, soil_moisture_pct=45, air_humidity_pct=55,
                              rainfall_mm=5, growth_stage="vegetative"))
    assert out["risk_level"] == "low"
    assert out["anomalies"] == []


def test_sensor_critical_low_soil_at_flowering_escalates_to_high():
    out = analyze(SensorInput(temperature_c=28, soil_moisture_pct=10, air_humidity_pct=40,
                              rainfall_mm=0, growth_stage="flowering"))
    assert out["risk_level"] == "high"
    assert any("soil moisture" in a for a in out["anomalies"])


def test_sensor_severe_heat_flagged():
    out = analyze(SensorInput(temperature_c=41, soil_moisture_pct=40, growth_stage="vegetative"))
    assert out["risk_level"] in {"elevated", "high"}
    assert any("severe-heat" in a or "heat-stress" in a for a in out["anomalies"])


def test_sensor_missing_fields_reported():
    out = analyze(SensorInput(temperature_c=30))
    assert set(["soil_moisture_pct", "air_humidity_pct", "rainfall_mm", "growth_stage"]).issubset(
        set(out["missing_fields"])
    )


def test_sensor_tool_contract_roundtrip():
    tool = build()
    rec = tool.execute({"temperature_c": 34, "soil_moisture_pct": 20, "air_humidity_pct": 40,
                        "rainfall_mm": 1, "growth_stage": "flowering"})
    assert rec.success
    assert rec.provider_used == "rules"
    assert "risk_level" in rec.output


def test_sensor_invalid_value_is_input_error():
    tool = build()
    rec = tool.execute({"soil_moisture_pct": 250})  # out of range
    assert not rec.success
    assert "invalid input" in (rec.error or "")

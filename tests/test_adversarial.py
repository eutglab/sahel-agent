"""Red-team scenarios A–F from the stress-test spec — locked as regression tests."""
from __future__ import annotations

import pytest

from app.agent.agent import run_agent
from app.core.schemas import AgentInput, Location, SensorReadings
from app.data.demo_data import get_scenario, load_scenario_image


@pytest.fixture(scope="module")
def demo_image():
    return load_scenario_image(get_scenario("multiple_risks"))


@pytest.fixture(scope="module")
def normal_image():
    return load_scenario_image(get_scenario("normal"))


def test_A_image_only_does_not_fabricate_sensors_or_weather(demo_image):
    r = run_agent(AgentInput(image_bytes=demo_image, text_context="observe what you can"))
    assert "analyze_image" in r.tools_used
    assert "analyze_sensor_data" not in r.tools_used
    assert "get_weather" not in r.tools_used
    assert r.observation.sensors is None
    assert r.observation.weather is None
    # No cross-check statement may reference sensor readings that don't exist.
    div = r.observation.risk["cross_check"]["diverging_evidence"]
    assert not any("sensor readings" in d for d in div)


def test_B_sensors_only_no_image_claim():
    r = run_agent(AgentInput(sensors=SensorReadings(
        temperature_c=39, soil_moisture_pct=18, air_humidity_pct=27, rainfall_mm=0, growth_stage="flowering")))
    assert "analyze_sensor_data" in r.tools_used
    assert "analyze_image" not in r.tools_used
    assert r.observation.vision is None


def test_C_image_plus_sensors_uses_both(demo_image):
    r = run_agent(AgentInput(
        image_bytes=demo_image,
        sensors=SensorReadings(temperature_c=34, soil_moisture_pct=20, growth_stage="vegetative")))
    assert {"analyze_image", "analyze_sensor_data"} <= set(r.tools_used)
    assert r.observation.vision and r.observation.sensors


def test_D_contradiction_is_detected_and_lowers_confidence(normal_image):
    r = run_agent(AgentInput(
        image_bytes=normal_image,
        sensors=SensorReadings(temperature_c=30, soil_moisture_pct=10, air_humidity_pct=30,
                               rainfall_mm=2, growth_stage="flowering"),
        location=Location(label="Fictional Site Beta", latitude=15.1, longitude=-3.4)))
    xc = r.observation.risk["cross_check"]
    assert xc["diverging_evidence"], "contradiction between image and sensors must be flagged"
    assert r.observation.risk["confidence"] <= 0.55
    assert "converge" in (r.recommendation["main_finding"].lower()) or "provisional" in r.recommendation["main_finding"].lower()


def test_E_incomplete_data_is_acknowledged():
    r = run_agent(AgentInput(sensors=SensorReadings(temperature_c=35)))
    missing = r.observation.sensors["missing_fields"]
    assert {"soil_moisture_pct", "air_humidity_pct", "rainfall_mm"} <= set(missing)
    assert float(r.recommendation["confidence"]) <= 0.5


def test_E_no_data_at_all_reports_unknown_not_low():
    r = run_agent(AgentInput())
    assert r.observation.risk["combined_risk"]["level"] == "unknown"
    assert "nsufficient" in r.situation_line()
    assert float(r.recommendation["confidence"]) <= 0.2


def test_F_impossible_values_are_flagged_and_ignored():
    r = run_agent(AgentInput(sensors=SensorReadings(
        temperature_c=-100, soil_moisture_pct=50, air_humidity_pct=50,
        rainfall_mm=999999, growth_stage="flowering")))
    anomalies = " ".join(r.observation.sensors["anomalies"])
    assert "outside the plausible range" in anomalies
    assert "temperature_c" in anomalies and "rainfall_mm" in anomalies
    # the impossible values must not drive the risk score
    drivers = " ".join(
        d for sub in ("water_stress", "heat_stress", "environmental")
        for d in r.observation.risk[sub]["drivers"]
    )
    assert "cold-stress" not in drivers


def test_F_out_of_schema_values_rejected_at_input():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SensorReadings(soil_moisture_pct=500)
    with pytest.raises(ValidationError):
        SensorReadings(air_humidity_pct=-20)


def test_scenario_id_path_traversal_is_neutralised():
    from app.data.demo_data import precomputed_result

    assert precomputed_result("../../../etc/passwd") is None
    assert precomputed_result("..%2f..%2fsecrets") is None
    assert precomputed_result("multiple_risks") is not None

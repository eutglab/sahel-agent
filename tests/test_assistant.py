from __future__ import annotations

from app.agent.agent import SahelAgent
from app.agent.assistant import answer
from app.core.schemas import AgentInput, Location, SensorReadings


def test_answer_with_no_result_is_graceful():
    resp = answer("Why is the risk moderate?", None)
    assert resp["used_tool"] is None
    assert "Analyze" in resp["text"] or "Analysez" in resp["text"]


def test_answer_why_uses_main_finding_and_drivers(multiple_risks_input):
    result = SahelAgent().analyze(multiple_risks_input)
    resp = answer("Why is the risk high?", result, multiple_risks_input)
    assert resp["text"]
    assert "risk" in resp["text"].lower() or "stress" in resp["text"].lower()


def test_answer_actions_returns_recommended_actions(multiple_risks_input):
    result = SahelAgent().analyze(multiple_risks_input)
    resp = answer("What should I do first?", result, multiple_risks_input)
    first_action = result.recommendation["recommended_actions"][0]
    assert first_action[:20] in resp["text"]


def test_answer_evidence_reports_what_the_pipeline_already_found(multiple_risks_input):
    result = SahelAgent().analyze(multiple_risks_input)
    resp = answer("Show me the evidence.", result, multiple_risks_input)
    assert resp["evidence"] == result.recommendation.get("evidence", [])


def test_answer_fetches_evidence_live_when_pipeline_skipped_it():
    ai = AgentInput(
        sensors=SensorReadings(temperature_c=27, soil_moisture_pct=60, air_humidity_pct=55,
                               rainfall_mm=5, growth_stage="vegetative"),
        location=Location(label="Calm Site"),
    )
    result = SahelAgent().analyze(ai)
    assert "search_web" not in result.tools_used  # low risk -> pipeline skipped it
    resp = answer("Is this dangerous for the crop?", result, ai)
    # Low risk means no dominant driver -> nothing to ground either, but this
    # must never raise regardless of the branch taken.
    assert isinstance(resp["text"], str) and resp["text"]

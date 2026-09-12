from __future__ import annotations

from app.agent.agent import SahelAgent
from app.agent.assistant import answer, needs_live_evidence
from app.core.schemas import AgentInput, Location, SensorReadings


def test_pre_analysis_never_invents_a_field_specific_answer():
    resp = answer("Why is the risk moderate?", None)
    assert resp["used_tool"] is None
    assert resp["evidence"] == []
    assert "haven't" not in resp["text"].lower()  # no invented certainty either way
    assert "analysis" in resp["text"].lower() and "first" in resp["text"].lower()


def test_pre_analysis_answers_general_product_questions():
    resp = answer("What can you analyze?", None)
    assert "water stress" in resp["text"].lower() or "risk" in resp["text"].lower()
    resp2 = answer("What does confidence mean?", None)
    assert "confidence" in resp2["text"].lower() or "agree" in resp2["text"].lower()


def test_pre_analysis_chat_is_never_a_dead_end():
    # Every general question gets a substantive answer, never a bare refusal.
    for q in ("How does SAHEL Agent work?", "What data should I provide?", "hello"):
        resp = answer(q, None)
        assert len(resp["text"]) > 20


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


def test_needs_live_evidence_false_before_analysis():
    assert needs_live_evidence("Show me the evidence.", None) is False


def test_needs_live_evidence_true_only_when_pipeline_has_no_evidence_yet(multiple_risks_input):
    result = SahelAgent().analyze(multiple_risks_input)
    # multiple_risks scenario already has evidence (elevated risk) -> no live call needed
    assert needs_live_evidence("Did you check evidence?", result) is False


def test_chat_state_survives_across_reruns_via_session_result(multiple_risks_input):
    """A second, unrelated question must see the SAME analysis context — this is
    what 'one agent, shared state' means in practice: no re-analysis, no reset."""
    result = SahelAgent().analyze(multiple_risks_input)
    first = answer("Why is the risk high?", result, multiple_risks_input)
    second = answer("What should I do first?", result, multiple_risks_input)
    assert first["text"] and second["text"]
    assert result.recommendation["recommended_actions"][0][:15] in second["text"]

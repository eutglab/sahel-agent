from __future__ import annotations

from app.tools.recommendation.providers.template import synthesize
from app.tools.recommendation.schema import RecommendationInput
from app.tools.recommendation.tool import build


def _risk(level="high"):
    sub = lambda lv: {"level": lv, "score": 0.8 if lv == "high" else 0.4, "drivers": []}
    return {
        "water_stress": sub(level),
        "heat_stress": sub("moderate"),
        "environmental": sub("low"),
        "combined_risk": sub(level),
        "cross_check": {"converging_evidence": ["sensors + weather agree"], "diverging_evidence": []},
        "confidence": 0.7,
    }


def test_recommendation_high_priority_has_actions():
    out = synthesize(RecommendationInput(risk=_risk("high"), growth_stage="flowering", modalities=["sensors"]))
    assert out["priority"] == "high"
    assert out["recommended_actions"]
    assert any("irrigation" in a.lower() for a in out["recommended_actions"])


def test_recommendation_always_has_warning_and_limitations():
    out = synthesize(RecommendationInput(risk=_risk("low"), modalities=[]))
    assert any("decision support" in w.lower() or "not agronomic" in w.lower() for w in out["warnings"])
    assert out["limitations"]


def test_recommendation_unknown_risk_is_low_priority():
    out = synthesize(RecommendationInput(risk=None, modalities=[]))
    assert out["priority"] == "low"
    assert "Insufficient data" in out["main_finding"]


def test_recommendation_tool_contract():
    tool = build()
    rec = tool.execute({"risk": _risk("high"), "growth_stage": "flowering", "modalities": ["sensors"]})
    assert rec.success
    assert rec.provider_used == "template"
    for key in ("priority", "main_finding", "recommended_actions", "confidence", "limitations"):
        assert key in rec.output

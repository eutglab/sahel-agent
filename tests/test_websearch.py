from __future__ import annotations

from app.agent.agent import SahelAgent
from app.core.schemas import AgentInput, GrowthStage, Location, SensorReadings
from app.tools.websearch.providers.mock import MockWebSearchProvider
from app.tools.websearch.schema import WebSearchInput
from app.tools.websearch.tool import build


def test_mock_websearch_is_deterministic():
    p = MockWebSearchProvider()
    a = p.run(WebSearchInput(query="heat stress advisory"))
    b = p.run(WebSearchInput(query="heat stress advisory"))
    assert a == b
    assert a["source"] == "sample (offline)"
    assert a["results"]


def test_websearch_tool_falls_back_to_mock_offline():
    tool = build()
    rec = tool.execute({"query": "irrigation advisory", "max_results": 3})
    assert rec.success
    # In demo mode Exa is skipped (offline_first); mock must answer.
    assert rec.provider_used == "mock"
    assert rec.output["results"]


def test_websearch_tool_has_terminal_provider():
    tool = build()
    assert tool.providers()[-1].name == "mock"


def test_agent_skips_web_search_when_risk_is_low():
    ai = AgentInput(
        sensors=SensorReadings(temperature_c=27, soil_moisture_pct=60, air_humidity_pct=55,
                                rainfall_mm=5, growth_stage=GrowthStage.vegetative),
        location=Location(label="Calm Site"),
    )
    result = SahelAgent().analyze(ai)
    assert "search_web" not in result.tools_used


def test_agent_calls_web_search_when_risk_is_elevated(multiple_risks_input):
    result = SahelAgent().analyze(multiple_risks_input)
    assert result.observation.risk["combined_risk"]["level"] in {"moderate", "high"}
    assert "search_web" in result.tools_used
    assert result.recommendation.get("evidence")
    assert result.recommendation.get("evidence_source") == "sample (offline)"

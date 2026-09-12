"""Offline guarantee: the full demo must work with no network access."""
from __future__ import annotations

import pytest

from app.agent.agent import run_agent
from app.core.schemas import AgentInput, Location, SensorReadings
from app.data.demo_data import list_scenarios, load_scenario_image

pytestmark = pytest.mark.offline


def test_all_demo_scenarios_run_offline(block_network):
    list_scenarios.cache_clear()
    scenarios = list_scenarios()
    assert len(scenarios) >= 5
    for scn in scenarios:
        ai = AgentInput(
            text_context=scn.get("text_context", ""),
            image_bytes=load_scenario_image(scn),
            image_name=scn.get("image"),
            sensors=SensorReadings(**scn.get("sensors", {})),
            location=Location(**scn.get("location", {})),
            scenario_id=scn["id"],
        )
        result = run_agent(ai)
        assert result.recommendation is not None, scn["id"]
        rec = result.recommendation
        for key in ("priority", "main_finding", "recommended_actions", "confidence", "limitations"):
            assert rec.get(key) not in (None, ""), (scn["id"], key)


def test_weather_tool_offline_uses_local_or_mock(block_network):
    from app.tools.weather.tool import build

    rec = build().execute({"label": "Fictional Site Alpha", "latitude": 14.5, "longitude": -4.2})
    assert rec.success
    assert rec.provider_used in {"local", "mock"}


def test_llm_client_is_mock_in_demo_mode(block_network):
    from app.llm.factory import get_llm_client

    assert get_llm_client().is_mock


def test_openrouter_never_touches_network_when_offline(block_network, monkeypatch):
    """Even with LLM_PROVIDER=openrouter configured and an API key set, offline
    /demo mode must never let the agent reach it — see `use_llm` in agent.py."""
    from app.agent.agent import SahelAgent
    from app.llm.providers.openrouter import OpenRouterLLMClient

    monkeypatch.setenv("OPENROUTER_API_KEY", "unused-in-offline-mode")
    agent = SahelAgent(llm=OpenRouterLLMClient())
    ai = AgentInput(
        sensors=SensorReadings(temperature_c=37, soil_moisture_pct=18, growth_stage="flowering"),
        location=Location(label="Fictional Site Alpha", latitude=14.5, longitude=-4.2),
    )
    result = agent.analyze(ai)
    assert result.reasoning_mode == "deterministic"
    assert result.recommendation is not None


def test_healthcheck_module_runs_offline(block_network, capsys):
    import healthcheck

    code = healthcheck.main()
    out = capsys.readouterr().out
    assert "STATUS:" in out
    assert code == 0

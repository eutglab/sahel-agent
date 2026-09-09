from __future__ import annotations

from app.agent.agent import SahelAgent, run_agent
from app.agent.planner import plan_tools
from app.core.schemas import AgentInput, Location, SensorReadings


def test_agent_runs_full_pipeline_on_multiple_risks(multiple_risks_input):
    result = run_agent(multiple_risks_input)
    assert result.recommendation is not None
    assert "analyze_sensor_data" in result.tools_used
    assert "calculate_risk" in result.tools_used
    assert "generate_recommendation" in result.tools_used
    assert result.observation.risk["combined_risk"]["level"] == "high"
    assert not result.degraded


def test_agent_skips_weather_and_vision_when_absent():
    ai = AgentInput(
        sensors=SensorReadings(temperature_c=36, soil_moisture_pct=20, growth_stage="fruiting"),
        location=Location(),
        scenario_id="incomplete_data",
    )
    result = run_agent(ai)
    assert "get_weather" not in result.tools_used
    assert "analyze_image" not in result.tools_used
    assert "analyze_sensor_data" in result.tools_used
    assert any("No location" in n for n in result.observation.notes)


def test_planner_is_modality_driven():
    available = ["analyze_image", "analyze_sensor_data", "get_weather",
                 "calculate_risk", "generate_recommendation"]
    only_sensors = AgentInput(sensors=SensorReadings(temperature_c=30, soil_moisture_pct=25))
    plan = plan_tools(only_sensors, available)
    assert plan == ["analyze_sensor_data", "calculate_risk", "generate_recommendation"]


def test_agent_trace_is_populated(multiple_risks_input):
    result = run_agent(multiple_risks_input)
    lines = result.trace.as_lines()
    assert any("Understanding input" in ln for ln in lines)
    assert any("Calling analyze_sensor_data" in ln for ln in lines)
    assert result.trace.tool_calls


def test_agent_level3_precomputed_on_reasoning_failure(monkeypatch, multiple_risks_input):
    agent = SahelAgent()

    def boom(*a, **k):
        raise RuntimeError("simulated planner failure")

    monkeypatch.setattr(agent, "_run_pipeline", boom)
    result = agent.analyze(multiple_risks_input)
    # Falls back to the frozen precomputed scenario result.
    assert result.reasoning_mode == "precomputed"
    assert result.recommendation is not None
    assert result.degraded


def test_agent_l1_llm_tool_calling_loop(monkeypatch):
    """With a non-mock LLM, the agent runs the tool-calling loop and can
    re-ask for more tools after seeing results."""
    import app.core.config as C
    from app.core.schemas import HealthState, HealthStatus, MaturityStatus
    from app.llm.base import LLMClient, LLMResponse, ToolInvocation

    class FakeLLM(LLMClient):
        name = "fake"
        status = MaturityStatus.INTEGRATION_READY  # -> not is_mock

        def complete(self, s, u, max_tokens=800):
            return LLMResponse(text="ok")

        def complete_with_tools(self, s, u, tools, tool_results=None, max_tokens=900):
            if tool_results:  # round 2: now ask for weather
                return LLMResponse(tool_calls=[ToolInvocation("get_weather", {})])
            return LLMResponse(tool_calls=[ToolInvocation("analyze_sensor_data", {})])

        def analyze_image(self, b, p):
            return LLMResponse(text="{}")

        def health_check(self):
            return HealthStatus(component="llm:fake", state=HealthState.READY)

    monkeypatch.setattr(C.settings, "demo_mode", False, raising=False)
    monkeypatch.setattr(C.settings, "environment", "real", raising=False)

    ai = AgentInput(
        sensors=SensorReadings(temperature_c=37, soil_moisture_pct=18, growth_stage="flowering"),
        location=Location(label="Fictional Site Alpha", latitude=14.5, longitude=-4.2),
    )
    result = SahelAgent(llm=FakeLLM()).analyze(ai)
    assert result.reasoning_mode == "llm_tool_calling"
    assert "analyze_sensor_data" in result.tools_used
    assert "get_weather" in result.tools_used          # added on the re-ask round
    assert "generate_recommendation" in result.tools_used
    assert any("round 2" in ln for ln in result.trace.as_lines())


def test_agent_continues_without_vision_on_bad_image():
    ai = AgentInput(
        image_bytes=b"this is not an image",
        sensors=SensorReadings(temperature_c=34, soil_moisture_pct=18, growth_stage="flowering"),
    )
    result = run_agent(ai)
    assert result.recommendation is not None
    assert result.observation.vision is None
    assert any("Vision unavailable" in n for n in result.observation.notes)


def test_agent_deterministic_fallback_without_scenario(monkeypatch):
    ai = AgentInput(sensors=SensorReadings(temperature_c=34, soil_moisture_pct=18, growth_stage="flowering"))
    agent = SahelAgent()
    calls = {"n": 0}
    real = agent._run_pipeline

    def flaky(planned, agent_input, trace):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("first path fails")
        return real(planned, agent_input, trace)

    monkeypatch.setattr(agent, "_run_pipeline", flaky)
    result = agent.analyze(ai)
    assert result.recommendation is not None  # deterministic fallback recovered it
    assert result.degraded

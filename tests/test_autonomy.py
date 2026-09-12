"""Agent Capability & Autonomy — the displayed mode/level must match reality:
what `AgentResult.reasoning_mode` and `.tools_used` actually say, and nothing
made up. See app/agent/autonomy.py for the exact ladder."""
from __future__ import annotations

from app.agent.autonomy import compute_autonomy
from app.core.schemas import AgentResult, ObservationBundle


def _result(*, reasoning_mode: str, tools_used, degraded: bool = False,
            modalities_used=None, observation: ObservationBundle | None = None,
            recommendation=None):
    return AgentResult(
        reasoning_mode=reasoning_mode,
        tools_used=list(tools_used),
        degraded=degraded,
        modalities_used=modalities_used or [],
        observation=observation or ObservationBundle(),
        recommendation=recommendation if recommendation is not None else {"priority": "moderate"},
    )


def test_pre_analysis_state_has_no_level_and_no_fabricated_score(registry):
    auto = compute_autonomy(None, registry)
    assert auto["level"] == 0
    assert auto["operating_mode"] == "Offline Demo"
    assert "not run" in auto["why"].lower() or "no analysis" in auto["why"].lower()


def test_precomputed_scenario_is_level_1_offline_demo(registry):
    result = _result(reasoning_mode="precomputed", tools_used=["calculate_risk", "generate_recommendation"])
    auto = compute_autonomy(result, registry)
    assert auto["level"] == 1
    assert auto["operating_mode"] == "Offline Demo"


def test_backbone_only_is_level_1(registry):
    """No observation tool ran (no image/sensors/weather) — just the fixed
    risk + recommendation backbone. That's guided, not orchestrated."""
    result = _result(reasoning_mode="deterministic", tools_used=["calculate_risk", "generate_recommendation"])
    auto = compute_autonomy(result, registry)
    assert auto["level"] == 1
    assert auto["operating_mode"] == "Deterministic Agent"


def test_observation_tools_plus_backbone_is_level_2_tool_orchestration(registry):
    result = _result(
        reasoning_mode="deterministic",
        tools_used=["analyze_sensor_data", "get_weather", "calculate_risk", "generate_recommendation"],
    )
    auto = compute_autonomy(result, registry)
    assert auto["level"] == 2
    assert auto["operating_mode"] == "Deterministic Agent"
    assert "Sensor analysis" in auto["active_capabilities"]


def test_search_web_used_is_level_3_adaptive_evidence_gathering(registry):
    result = _result(
        reasoning_mode="deterministic",
        tools_used=["analyze_sensor_data", "get_weather", "calculate_risk", "search_web", "generate_recommendation"],
    )
    auto = compute_autonomy(result, registry)
    assert auto["level"] == 3
    assert "External evidence search (Exa)" in auto["active_capabilities"]
    assert any("evidence" in n.lower() for n in auto["notes"])


def test_llm_tool_calling_with_evidence_reports_llm_plus_evidence_mode(registry):
    result = _result(
        reasoning_mode="llm_tool_calling",
        tools_used=["analyze_sensor_data", "get_weather", "calculate_risk", "search_web", "generate_recommendation"],
    )
    auto = compute_autonomy(result, registry)
    assert auto["level"] == 3
    assert auto["operating_mode"] == "LLM + External Evidence"


def test_llm_tool_calling_without_evidence_reports_llm_tool_calling_mode(registry):
    result = _result(
        reasoning_mode="llm_tool_calling",
        tools_used=["analyze_sensor_data", "calculate_risk", "generate_recommendation"],
    )
    auto = compute_autonomy(result, registry)
    assert auto["level"] == 2
    assert auto["operating_mode"] == "LLM Tool-Calling"


def test_level_4_is_never_reached_and_always_listed_as_unavailable(registry):
    """Nothing in this codebase actuates the physical world — level 4 must
    never appear as an achieved level, and must always be disclosed as such."""
    for tools in (
        ["calculate_risk", "generate_recommendation"],
        ["analyze_image", "analyze_sensor_data", "get_weather", "calculate_risk", "generate_recommendation"],
        ["analyze_sensor_data", "get_weather", "calculate_risk", "search_web", "generate_recommendation"],
    ):
        auto = compute_autonomy(_result(reasoning_mode="deterministic", tools_used=tools), registry)
        assert auto["level"] < 4
    assert any("physical action" in c.lower() for c in compute_autonomy(None, registry)["unavailable_capabilities"])


def test_unavailable_capabilities_reflect_registry_status_not_a_fixed_list(registry):
    auto = compute_autonomy(None, registry)
    # file_analysis / notification are disabled by default config -> not registered
    # at all, so they simply don't appear as "active"; the physical-action line
    # is always present regardless of registry contents.
    assert "Physical action / equipment control (not implemented)" in auto["unavailable_capabilities"]
    for cap in auto["active_capabilities"]:
        assert cap != "Physical action / equipment control (not implemented)"


def test_missing_modalities_are_disclosed_as_a_constraint(registry):
    result = _result(
        reasoning_mode="deterministic",
        tools_used=["analyze_sensor_data", "calculate_risk", "generate_recommendation"],
        modalities_used=["sensors"],
    )
    auto = compute_autonomy(result, registry)
    assert any("missing input" in c.lower() for c in auto["constraints"])


def test_degraded_run_is_disclosed_as_a_constraint(registry):
    result = _result(
        reasoning_mode="deterministic",
        tools_used=["analyze_sensor_data", "get_weather", "calculate_risk", "generate_recommendation"],
        degraded=True,
    )
    auto = compute_autonomy(result, registry)
    assert any("fallback" in c.lower() for c in auto["constraints"])


def test_autonomy_matches_a_real_agent_run_end_to_end(multiple_risks_input):
    """Integration check: run the real agent on the primary demo scenario and
    confirm the computed level is consistent with what actually executed —
    not asserting a hardcoded expected level, but the invariant that level
    3 <=> search_web actually ran, and level is never fabricated as 4."""
    from app.agent.agent import run_agent
    from app.tools.registry import get_registry

    result = run_agent(multiple_risks_input)
    auto = compute_autonomy(result, get_registry())
    assert auto["level"] < 4
    assert (auto["level"] == 3) == ("search_web" in result.tools_used)
    assert len(auto["active_capabilities"]) == len(result.tools_used)

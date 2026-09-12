"""Agent Capability & Autonomy — an honest summary of what the agent actually
did on one run, for judges who want to know "how autonomous is this, really?"
without reading the trace line by line.

Every field here is derived only from ``AgentResult`` (what actually executed)
and the tool registry (what is actually wired) — nothing is a fabricated score
like "95% autonomous". The level is a fixed 4-rung ladder tied to observable
facts (which tools ran, which reasoning path produced them):

    1  Guided analysis            — only the risk/recommendation backbone ran
    2  Tool orchestration         — the agent selected + ran observation tools
                                     and fused their results
    3  Adaptive evidence gathering — the agent decided, from the risk level it
                                     computed, to search for external evidence
    4  External action/integration — NEVER reached: nothing in this codebase
                                     actuates anything in the physical world
                                     (see docs/roadmap.md) — always reported as
                                     not implemented, never claimed.

See docs/agent_design.md for the reasoning-mode ladder this reads from
(``AgentResult.reasoning_mode``: llm_tool_calling / deterministic / precomputed).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.schemas import AgentResult, MaturityStatus
from app.tools.registry import ToolRegistry

_OBSERVATION_TOOLS = {"analyze_image", "analyze_sensor_data", "get_weather"}

_LEVEL_LABELS = {
    1: "Level 1 — Guided analysis",
    2: "Level 2 — Tool orchestration",
    3: "Level 3 — Adaptive evidence gathering",
    4: "Level 4 — External action / integration",
}

_CAPABILITY_LABELS = {
    "analyze_image": "Image analysis",
    "analyze_sensor_data": "Sensor analysis",
    "get_weather": "Weather lookup",
    "calculate_risk": "Risk calculation",
    "generate_recommendation": "Recommendation generation",
    "search_web": "External evidence search (Exa)",
    "file_analysis": "File analysis",
    "notification": "Notifications",
}

_NOT_AUTOMATED = "Physical action / equipment control (not implemented)"

_TERMINAL_STATUSES = (MaturityStatus.IMPLEMENTED, MaturityStatus.MOCKED)


def _label(name: str) -> str:
    return _CAPABILITY_LABELS.get(name, name)


def _capability_lists(registry: ToolRegistry) -> tuple[List[str], List[str]]:
    active = [_label(t.name) for t in registry.tools() if t.status in _TERMINAL_STATUSES]
    unavailable = [_label(t.name) for t in registry.tools() if t.status not in _TERMINAL_STATUSES]
    unavailable.append(_NOT_AUTOMATED)
    return active, unavailable


def compute_autonomy(result: Optional[AgentResult], registry: ToolRegistry) -> Dict[str, Any]:
    """Everything the UI needs to render the Agent Capability & Autonomy card."""
    active, unavailable = _capability_lists(registry)

    if result is None:
        return {
            "operating_mode": "Offline Demo",
            "level": 0,
            "level_label": "Not yet analyzed",
            "active_capabilities": active,
            "unavailable_capabilities": unavailable,
            "why": (
                "No analysis has run yet. The mode and level below are computed from what "
                "actually executes on Analyze Field, not a fixed rating."
            ),
            "constraints": _static_constraints(),
            "notes": ["No analysis has run yet."],
        }

    tools = set(result.tools_used)
    has_observation = bool(tools & _OBSERVATION_TOOLS)
    has_evidence = "search_web" in tools

    if result.reasoning_mode == "precomputed":
        operating_mode = "Offline Demo"
        level = 1
    elif has_evidence:
        operating_mode = "LLM + External Evidence" if result.reasoning_mode == "llm_tool_calling" else "Deterministic Agent"
        level = 3
    elif has_observation:
        operating_mode = "LLM Tool-Calling" if result.reasoning_mode == "llm_tool_calling" else "Deterministic Agent"
        level = 2
    else:
        operating_mode = "LLM Tool-Calling" if result.reasoning_mode == "llm_tool_calling" else "Deterministic Agent"
        level = 1

    return {
        "operating_mode": operating_mode,
        "level": level,
        "level_label": _LEVEL_LABELS[level],
        "active_capabilities": [_label(n) for n in sorted(tools)],
        "unavailable_capabilities": unavailable,
        "why": _why(result, level),
        "constraints": _static_constraints() + _dynamic_constraints(result),
        "notes": _dynamic_notes(result),
    }


def _why(result: AgentResult, level: int) -> str:
    n = len(result.tools_used)
    if result.reasoning_mode == "precomputed":
        return (
            "This run served a frozen precomputed scenario (the Level 3 fallback in the "
            "reasoning ladder, docs/architecture.md) — no live tool orchestration happened."
        )
    if level == 3:
        return (
            f"The agent selected and ran {n} tool(s), then decided on its own — because the "
            "risk it computed was moderate or high — to search for external evidence before "
            "recommending actions."
        )
    if level == 2:
        return (
            f"The agent selected and ran {n} tool(s) across the inputs provided, then "
            "cross-checked and fused their results into one recommendation."
        )
    return (
        f"Only the core risk/recommendation step ran ({n} tool(s)). Provide an image, sensor "
        "readings or a location for the agent to orchestrate more tools."
    )


def _dynamic_notes(result: AgentResult) -> List[str]:
    tools = set(result.tools_used)
    obs = result.observation
    notes = [f"Agent selected {len(tools)} tool(s): {', '.join(sorted(tools)) or 'none'}."]
    if obs.sensors and obs.weather:
        notes.append("Sensor and weather results cross-checked against each other.")
    elif obs.vision and obs.sensors:
        notes.append("Image and sensor results cross-checked against each other.")
    if "search_web" in tools:
        notes.append("External evidence searched because the computed risk was elevated.")
    elif result.reasoning_mode != "precomputed":
        notes.append("External evidence not searched — risk level did not warrant it.")
    if result.recommendation:
        notes.append("Recommendation generated from the available evidence.")
    notes.append("No physical action was executed — this is decision support only.")
    if len(result.modalities_used) < 3:
        notes.append("Confidence is limited by missing field measurements (image, sensors or location).")
    return notes


def _static_constraints() -> List[str]:
    return [
        "Risk scores are prototype heuristics, not a validated agronomic model.",
        "Vision output is possible signs, never a diagnosis.",
        "The agent never controls physical equipment or takes real-world action.",
    ]


def _dynamic_constraints(result: AgentResult) -> List[str]:
    out: List[str] = []
    if result.degraded:
        out.append("This run used a fallback reasoning path — see Run details for why.")
    missing = {"image", "sensors", "location"} - set(result.modalities_used)
    if missing:
        out.append(f"Missing input(s) for this run: {', '.join(sorted(missing))}.")
    return out

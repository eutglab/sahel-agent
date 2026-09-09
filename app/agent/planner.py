"""Deterministic tool planner — the rule-based reasoning path (Level 2).

Honestly rule-based: it selects tools purely from which modalities are present.
Used when no real LLM is configured, in offline/demo mode, or as a fallback when
the LLM path fails schema validation.
"""
from __future__ import annotations

from typing import List

from app.core.schemas import AgentInput


def plan_tools(agent_input: AgentInput, available: List[str]) -> List[str]:
    """Return an ordered list of tool names to execute."""
    mods = set(agent_input.available_modalities())
    plan: List[str] = []

    if "image" in mods and "analyze_image" in available:
        plan.append("analyze_image")
    if "sensors" in mods and "analyze_sensor_data" in available:
        plan.append("analyze_sensor_data")
    # Weather is useful whenever we have a place to ask about.
    if "location" in mods and "get_weather" in available:
        plan.append("get_weather")

    # Synthesis backbone — always, if the tools exist.
    if "calculate_risk" in available:
        plan.append("calculate_risk")
    if "generate_recommendation" in available:
        plan.append("generate_recommendation")

    return plan


def plan_notes(agent_input: AgentInput) -> List[str]:
    """Human-readable notes about what was and was not available."""
    mods = set(agent_input.available_modalities())
    notes: List[str] = []
    if "image" not in mods:
        notes.append("No image supplied — skipping visual analysis.")
    if "sensors" not in mods:
        notes.append("No sensor readings supplied — skipping sensor analysis.")
    if "location" not in mods:
        notes.append("No location supplied — skipping weather retrieval.")
    return notes

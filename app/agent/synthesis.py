"""Merge individual tool outputs into one ObservationBundle (multimodal fusion)."""
from __future__ import annotations

from typing import Dict

from app.core.schemas import AgentInput, ObservationBundle, ToolCallRecord


def build_bundle(agent_input: AgentInput, records: Dict[str, ToolCallRecord], notes) -> ObservationBundle:
    bundle = ObservationBundle(modalities=agent_input.available_modalities(), notes=list(notes))

    vis = records.get("analyze_image")
    if vis and vis.success:
        bundle.vision = vis.output
    elif vis and vis.error:
        bundle.notes.append(f"Vision unavailable: {vis.error}")

    sen = records.get("analyze_sensor_data")
    if sen and sen.success:
        bundle.sensors = sen.output
    elif sen and sen.error:
        bundle.notes.append(f"Sensor analysis unavailable: {sen.error}")

    wx = records.get("get_weather")
    if wx and wx.success:
        bundle.weather = wx.output

    rk = records.get("calculate_risk")
    if rk and rk.success:
        bundle.risk = rk.output

    return bundle


def risk_input_from_records(agent_input: AgentInput, records: Dict[str, ToolCallRecord]) -> dict:
    def out(name: str):
        rec = records.get(name)
        return rec.output if rec and rec.success else None

    return {
        "sensors": out("analyze_sensor_data"),
        "vision": out("analyze_image"),
        "weather": out("get_weather"),
        "growth_stage": agent_input.sensors.growth_stage.value,
    }


def recommendation_input_from_records(agent_input: AgentInput, records: Dict[str, ToolCallRecord]) -> dict:
    def out(name: str):
        rec = records.get(name)
        return rec.output if rec and rec.success else None

    return {
        "sensors": out("analyze_sensor_data"),
        "vision": out("analyze_image"),
        "weather": out("get_weather"),
        "risk": out("calculate_risk"),
        "growth_stage": agent_input.sensors.growth_stage.value,
        "modalities": agent_input.available_modalities(),
    }

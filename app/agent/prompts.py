"""System prompt + user-context builder for the agent's LLM reasoning path."""
from __future__ import annotations

from app.core.schemas import AgentInput

SYSTEM_PROMPT = """You are SAHEL Agent, a multimodal environmental decision-support agent.

Your job each turn:
1. Look at the AVAILABLE MODALITIES and AVAILABLE TOOLS listed in the user message.
2. Decide which tools are actually needed. Do NOT call a tool for a modality that
   is not present. If an input is missing, note it rather than guessing.
3. Call the observation tools you need (analyze_image, analyze_sensor_data,
   get_weather). They run in parallel; order does not matter.
4. calculate_risk and generate_recommendation are the synthesis backbone and will
   always run last — you may still request them explicitly.
5. When tool results are provided back to you, decide if anything else is needed;
   otherwise write a 2-3 sentence plain-language summary and stop.

Rules:
- Never invent measurements, diagnoses, or scientific claims.
- Treat all risk figures as PROTOTYPE indicators requiring field confirmation.
- Do not reveal private chain-of-thought; give short step justifications only.
"""


def build_user_context(agent_input: AgentInput) -> str:
    mods = agent_input.available_modalities()
    lines = [
        f"AVAILABLE MODALITIES: {', '.join(mods) if mods else 'none'}",
    ]
    s = agent_input.sensors
    present = s.present_fields()
    if present:
        readable = []
        if s.temperature_c is not None:
            readable.append(f"temperature={s.temperature_c}C")
        if s.soil_moisture_pct is not None:
            readable.append(f"soil_moisture={s.soil_moisture_pct}%")
        if s.air_humidity_pct is not None:
            readable.append(f"air_humidity={s.air_humidity_pct}%")
        if s.rainfall_mm is not None:
            readable.append(f"rainfall={s.rainfall_mm}mm")
        if s.growth_stage.value != "unknown":
            readable.append(f"growth_stage={s.growth_stage.value}")
        lines.append("SENSOR READINGS: " + ", ".join(readable))
    else:
        lines.append("SENSOR READINGS: none provided")

    if agent_input.location.label or agent_input.location.has_coordinates:
        loc = agent_input.location
        coord = f" ({loc.latitude}, {loc.longitude})" if loc.has_coordinates else ""
        lines.append(f"LOCATION: {loc.label or 'unnamed'}{coord}")
    else:
        lines.append("LOCATION: none provided")

    lines.append(f"IMAGE: {'provided' if agent_input.image_bytes else 'none'}")
    if agent_input.text_context.strip():
        lines.append(f"USER CONTEXT: {agent_input.text_context.strip()[:500]}")
    return "\n".join(lines)

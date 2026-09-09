"""SAHEL Agent — the agentic loop with 3-level graceful degradation.

    Level 1  LLM tool-calling      (real reasoning; the model picks tools)
    Level 2  Deterministic planner (rule-based tool selection)
    Level 3  Precomputed scenario  (frozen result; demo never dies)

The agent only ever talks to the Tool Registry. Every step is recorded on an
AgentTrace and one JSON row is written per run (Run Details / benchmark).
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

from app.agent.planner import plan_notes, plan_tools
from app.agent.prompts import SYSTEM_PROMPT, build_user_context
from app.agent.synthesis import (
    build_bundle,
    recommendation_input_from_records,
    risk_input_from_records,
)
from app.core.config import settings
from app.core.logging import RunLogger, get_logger
from app.core.schemas import (
    AgentInput,
    AgentResult,
    AgentTrace,
    ObservationBundle,
    ToolCallRecord,
)
from app.llm.base import LLMClient, ToolSpec
from app.llm.factory import get_llm_client
from app.tools.registry import ToolRegistry, get_registry

logger = get_logger("sahel.agent")

_OBSERVATION_TOOLS = ["analyze_image", "analyze_sensor_data", "get_weather"]
_BACKBONE_TOOLS = ["calculate_risk", "generate_recommendation"]


class SahelAgent:
    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        llm: Optional[LLMClient] = None,
    ) -> None:
        self.registry = registry or get_registry()
        self.llm = llm or get_llm_client()

    # ------------------------------------------------------------------ #
    def analyze(self, agent_input: AgentInput) -> AgentResult:
        start = time.time()
        trace = AgentTrace()
        run_logger = RunLogger()
        mods = agent_input.available_modalities()

        trace.event("Understanding input", "ok", f"modalities: {', '.join(mods) or 'none'}")
        for note in plan_notes(agent_input):
            trace.event(note, "info")

        usable = self.registry.usable()
        records: Dict[str, ToolCallRecord] = {}
        degraded = False
        errors: List[str] = []

        use_llm = (not self.llm.is_mock) and (not settings.offline_first)
        reasoning_mode = "llm_tool_calling" if use_llm else "deterministic"

        try:
            if use_llm:
                trace.event("Selecting tools with LLM", "ok", f"provider: {self.llm.name}")
                records = self._llm_loop(agent_input, usable, trace)
                if not any(r.success for r in records.values()):
                    raise RuntimeError("LLM path produced no successful tool call")
            else:
                why = "offline/demo mode" if settings.offline_first else "no real LLM provider"
                trace.event("Selecting tools with rule-based planner", "ok", why)
                planned = plan_tools(agent_input, usable)
                records = self._run_pipeline(planned, agent_input, trace)
        except Exception as exc:  # noqa: BLE001 - fall to Level 3 / partial result
            degraded = True
            errors.append(f"reasoning path failed: {exc}")
            logger.warning("agent reasoning failed (%s); attempting fallback", exc)
            trace.event("Reasoning path failed — falling back", "error", str(exc)[:160])
            fallback = self._level3_precomputed(agent_input, trace)
            if fallback is not None:
                fallback.execution_ms = round((time.time() - start) * 1000, 1)
                self._log(run_logger, fallback, trace, success=True, degraded=True, errors=errors)
                return fallback
            # No precomputed scenario — degrade to deterministic planner.
            reasoning_mode = "deterministic"
            try:
                planned = plan_tools(agent_input, usable)
                records = self._run_pipeline(planned, agent_input, trace)
            except Exception as exc2:  # noqa: BLE001
                errors.append(f"deterministic fallback also failed: {exc2}")

        # Ensure the synthesis backbone ran even if the LLM skipped it.
        for name in _BACKBONE_TOOLS:
            if name in usable and name not in records:
                self._run_one(name, agent_input, records, trace)

        notes = plan_notes(agent_input)
        bundle: ObservationBundle = build_bundle(agent_input, records, notes)

        rec_rec = records.get("generate_recommendation")
        recommendation = rec_rec.output if (rec_rec and rec_rec.success) else None
        if recommendation is None:
            errors.append("no recommendation produced")
            degraded = True

        tools_used = [n for n, r in records.items() if r.success]
        trace.tool_calls = list(records.values())
        trace.event("Synthesis complete", "ok", f"tools used: {', '.join(tools_used) or 'none'}")

        result = AgentResult(
            scenario_id=agent_input.scenario_id,
            reasoning_mode=reasoning_mode,
            modalities_used=mods,
            tools_used=tools_used,
            observation=bundle,
            recommendation=recommendation,
            trace=trace,
            execution_ms=round((time.time() - start) * 1000, 1),
            degraded=degraded or bool(errors),
            errors=errors,
        )
        self._log(run_logger, result, trace, success=recommendation is not None, degraded=result.degraded, errors=errors)
        return result

    # ------------------------------------------------------------------ #
    def _llm_loop(
        self, agent_input: AgentInput, usable: List[str], trace: AgentTrace
    ) -> Dict[str, ToolCallRecord]:
        """L1: let the model pick observation tools, run them, and re-ask with
        the results up to AGENT_MAX_ITERATIONS times before the backbone runs."""
        specs = [
            ToolSpec(name=s["name"], description=s["description"], input_schema=s["input_schema"])
            for s in self.registry.describe_for_llm(only=usable)
        ]
        user = build_user_context(agent_input)
        records: Dict[str, ToolCallRecord] = {}
        tool_results: List[Dict[str, Any]] = []

        max_iters = max(1, settings.agent_max_iterations)
        for i in range(max_iters):
            resp = self.llm.complete_with_tools(
                SYSTEM_PROMPT, user, specs,
                tool_results=tool_results or None,
                max_tokens=700,
            )
            wanted = self._applicable(
                [c.name for c in resp.tool_calls], agent_input, usable, trace
            )
            new = [n for n in wanted if n in _OBSERVATION_TOOLS and n not in records]
            if not new:
                if i == 0:
                    trace.event("LLM requested no observation tools", "warn")
                break
            trace.event(
                f"LLM tool plan (round {i + 1})", "ok", ", ".join(new)
            )
            for name in new:
                self._run_one(name, agent_input, records, trace)
                rec = records.get(name)
                if rec:
                    tool_results.append(
                        {"tool": name, "success": rec.success, "output": rec.output, "error": rec.error}
                    )

        # Backbone always runs (enforced again by the caller as a safety net).
        for name in _BACKBONE_TOOLS:
            if name in usable and name not in records:
                self._run_one(name, agent_input, records, trace)
        return records

    def _applicable(
        self, requested: List[str], agent_input: AgentInput, usable: List[str], trace: AgentTrace
    ) -> List[str]:
        mods = set(agent_input.available_modalities())
        need = {"analyze_image": "image", "analyze_sensor_data": "sensors", "get_weather": "location"}
        out: List[str] = []
        for name in requested:
            if name not in usable:
                continue
            if name in need and need[name] not in mods:
                trace.event(f"LLM asked for {name} but no {need[name]} present — skipped", "warn")
                continue
            if name not in out:
                out.append(name)
        return out

    # ------------------------------------------------------------------ #
    def _run_pipeline(
        self, planned: List[str], agent_input: AgentInput, trace: AgentTrace
    ) -> Dict[str, ToolCallRecord]:
        records: Dict[str, ToolCallRecord] = {}
        for name in planned:
            self._run_one(name, agent_input, records, trace)
        return records

    def _run_one(
        self,
        name: str,
        agent_input: AgentInput,
        records: Dict[str, ToolCallRecord],
        trace: AgentTrace,
    ) -> None:
        if name in records:
            return
        if not self.registry.has(name):
            trace.event(f"Tool '{name}' not registered — skipped", "warn")
            return
        tool = self.registry.get(name)
        raw_input = self._tool_input(name, agent_input, records)
        if raw_input is None:
            trace.event(f"Skipping {name} (no applicable input)", "info")
            return

        trace.event(f"Calling {name}", "info")
        record = tool.execute(raw_input)
        records[name] = record
        if record.success:
            trace.event(f"{name} done", "ok", record.source_note or (record.provider_used or ""))
        else:
            trace.event(f"{name} failed", "error", (record.error or "")[:160])

    def _tool_input(self, name: str, agent_input: AgentInput, records: Dict[str, ToolCallRecord]):
        if name == "analyze_image":
            if not agent_input.image_bytes:
                return None
            return {"image_bytes": agent_input.image_bytes, "hint": agent_input.text_context[:300]}
        if name == "analyze_sensor_data":
            s = agent_input.sensors
            if not s.present_fields():
                return None
            return s.model_dump()
        if name == "get_weather":
            loc = agent_input.location
            if not (loc.label or loc.has_coordinates):
                return None
            return {"label": loc.label, "latitude": loc.latitude, "longitude": loc.longitude}
        if name == "calculate_risk":
            return risk_input_from_records(agent_input, records)
        if name == "generate_recommendation":
            return recommendation_input_from_records(agent_input, records)
        # external / unknown tools: pass a permissive dict
        return {}

    # ------------------------------------------------------------------ #
    def _level3_precomputed(self, agent_input: AgentInput, trace: AgentTrace) -> Optional[AgentResult]:
        if not agent_input.scenario_id:
            return None
        from app.data.demo_data import precomputed_result

        data = precomputed_result(agent_input.scenario_id)
        if not data:
            return None
        trace.event("Loaded precomputed scenario result", "ok", agent_input.scenario_id)
        bundle = ObservationBundle.model_validate(data.get("observation", {}))
        result = AgentResult(
            scenario_id=agent_input.scenario_id,
            reasoning_mode="precomputed",
            modalities_used=data.get("modalities_used", agent_input.available_modalities()),
            tools_used=data.get("tools_used", []),
            observation=bundle,
            recommendation=data.get("recommendation"),
            trace=trace,
            degraded=True,
            errors=["served precomputed fallback (Level 3)"],
        )
        return result

    def _log(self, run_logger: RunLogger, result: AgentResult, trace: AgentTrace, *, success, degraded, errors):
        provider_map: Dict[str, str] = {}
        for call in trace.tool_calls:
            if call.provider_used:
                provider_map[call.tool_name] = call.provider_used
        try:
            run_logger.write(
                scenario_id=result.scenario_id,
                reasoning_mode=result.reasoning_mode,
                tools_used=result.tools_used,
                provider_map=provider_map,
                execution_ms=result.execution_ms,
                success=success,
                degraded=degraded,
                errors=errors,
                trace_lines=trace.as_lines(),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("run logging failed: %s", exc)


def run_agent(agent_input: AgentInput) -> AgentResult:
    """Convenience wrapper used by the UI, scripts and tests."""
    return SahelAgent().analyze(agent_input)

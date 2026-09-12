"""Ask the Agent — a conversational panel over the current analysis.

Not a generic chatbot: it never invents facts. It answers from the SAME
structured result the main pipeline already produced (risk, recommendation,
evidence, limitations), and — the one genuinely agentic step — can trigger
the existing ``search_web`` tool itself, live, if a question needs evidence
that wasn't already fetched (because risk was low and the pipeline skipped
it). No new tool is added; this only calls tools already in the registry.

Mirrors the main agent's own two-level honesty: a deterministic keyword
router by default (same spirit as the L2 planner), and a real LLM — grounded
on this same structured context, never free-associating — only when one is
actually configured and online (same spirit as L1). Any LLM failure falls
back to the router silently; the panel never breaks.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.errors import ProviderError
from app.core.logging import get_logger
from app.core.schemas import AgentInput, AgentResult
from app.llm.factory import get_llm_client
from app.tools.registry import get_registry

logger = get_logger("sahel.assistant")

SUGGESTED_QUESTIONS = [
    "Why is the risk moderate?",
    "What should I do first?",
    "Show me the evidence.",
]

_SYSTEM = (
    "You are the conversational interface of SAHEL Agent, an environmental "
    "decision-support tool. Answer ONLY using the STRUCTURED ANALYSIS JSON given "
    "below — never invent numbers, sources or facts absent from it. Be concise: "
    "2-4 sentences, plain language, no chain-of-thought. If the analysis doesn't "
    "cover what's asked, say so plainly rather than guessing."
)


def _context(result: AgentResult) -> Dict[str, Any]:
    obs = result.observation
    risk = obs.risk or {}
    rec = result.recommendation or {}
    return {
        "combined_risk": (risk.get("combined_risk") or {}).get("level", "unknown"),
        "water_stress": risk.get("water_stress") or {},
        "heat_stress": risk.get("heat_stress") or {},
        "environmental": risk.get("environmental") or {},
        "cross_check": risk.get("cross_check") or {},
        "main_finding": rec.get("main_finding", ""),
        "recommended_actions": rec.get("recommended_actions", []),
        "confidence": rec.get("confidence", risk.get("confidence", 0)),
        "limitations": rec.get("limitations", []),
        "evidence": rec.get("evidence", []),
        "evidence_source": rec.get("evidence_source", ""),
        "modalities": obs.modalities,
    }


def _dominant_driver(ctx: Dict[str, Any]) -> Optional[str]:
    best_key, best_score = None, -1.0
    for key in ("water_stress", "heat_stress", "environmental"):
        sub = ctx.get(key) or {}
        if sub.get("level") in {"moderate", "high"} and float(sub.get("score", 0)) > best_score:
            best_key, best_score = key, float(sub.get("score", 0))
    return best_key


def _maybe_fetch_evidence(ctx: Dict[str, Any], agent_input: Optional[AgentInput]) -> List[Dict[str, Any]]:
    """The agentic step: call the existing search_web tool live, if the pipeline
    didn't already, and there's a real risk driver worth grounding."""
    driver = _dominant_driver(ctx)
    if not driver:
        return []
    registry = get_registry()
    if not registry.has("search_web"):
        return []
    topic = {
        "water_stress": "irrigation and water stress management advisory",
        "heat_stress": "heat stress crop management advisory",
        "environmental": "crop disease and pest advisory",
    }[driver]
    stage = agent_input.sensors.growth_stage.value if agent_input else "unknown"
    loc = (agent_input.location.label if agent_input and agent_input.location else None) or "Sahel region smallholder farm"
    query = f"{topic} {stage} stage {loc}".strip()
    record = registry.get("search_web").execute({"query": query, "max_results": 3})
    if not record.success:
        return []
    return (record.output or {}).get("results", [])


def _route(question: str, ctx: Dict[str, Any]) -> str:
    q = question.lower()

    if any(k in q for k in ("why", "reason", "cause")):
        driver = _dominant_driver(ctx)
        finding = ctx["main_finding"] or "No finding was produced."
        if driver:
            drivers = ", ".join((ctx[driver].get("drivers") or [])[:2]) or "no single named driver"
            return f"{finding} Contributing factor(s): {drivers}."
        return finding

    if any(k in q for k in ("what should", "do first", "next step", "action")):
        actions = ctx["recommended_actions"]
        if not actions:
            return "No specific action is indicated by the current analysis."
        return " ".join(f"{i + 1}. {a}" for i, a in enumerate(actions[:2]))

    if any(k in q for k in ("evidence", "source", "check", "danger", "safe", "confirm")):
        if ctx["evidence"]:
            src = "live web search (Exa)" if ctx["evidence_source"] == "exa" else "offline sample data"
            names = "; ".join(e.get("title", "source") for e in ctx["evidence"][:3])
            return f"Yes — {len(ctx['evidence'])} source(s) via {src}: {names}."
        return (
            f"Risk was assessed as {ctx['combined_risk']}, so no external evidence lookup "
            "was triggered for this analysis."
        )

    if "water" in q:
        sub = ctx["water_stress"]
        drivers = ", ".join(sub.get("drivers", [])[:2]) or "no specific driver logged"
        return f"Water stress is {sub.get('level', 'unknown')}. {drivers}."

    if any(k in q for k in ("heat", "temperature")):
        sub = ctx["heat_stress"]
        drivers = ", ".join(sub.get("drivers", [])[:2]) or "no specific driver logged"
        return f"Heat stress is {sub.get('level', 'unknown')}. {drivers}."

    if any(k in q for k in ("missing", "what information", "what data")):
        lims = ctx["limitations"]
        return " ".join(lims[:2]) if lims else "No missing-input limitations were logged for this run."

    if "would change" in q or "improve" in q:
        return (
            "Providing whichever modality is currently missing (image, sensor readings or "
            "location) would sharpen this assessment — see Limitations in Technical Details."
        )

    return (
        f"{ctx['main_finding'] or 'No finding available.'} "
        f"Confidence: {float(ctx['confidence'] or 0):.0%}. "
        "Ask me about water stress, heat stress, the evidence, or recommended actions."
    )


def answer(question: str, result: Optional[AgentResult], agent_input: Optional[AgentInput] = None) -> Dict[str, Any]:
    """Answer ``question`` about ``result``. Never raises."""
    import app.core.i18n as _i18n  # local import: keep this module UI-framework-agnostic

    if result is None:
        return {"text": _i18n.t("chat_empty", "en"), "evidence": [], "used_tool": None}

    ctx = _context(result)
    used_tool = None
    if not ctx["evidence"] and any(
        k in question.lower() for k in ("evidence", "source", "danger", "safe", "confirm")
    ):
        fetched = _maybe_fetch_evidence(ctx, agent_input)
        if fetched:
            ctx["evidence"] = fetched
            ctx["evidence_source"] = "exa"
            used_tool = "search_web"

    client = get_llm_client()
    if not client.is_mock and not settings.offline_first:
        try:
            prompt = "STRUCTURED ANALYSIS:\n" + json.dumps(ctx, default=str)[:5000] + f"\n\nQUESTION: {question}"
            resp = client.complete(_SYSTEM, prompt, max_tokens=250)
            if resp.text.strip():
                return {"text": resp.text.strip(), "evidence": ctx["evidence"], "used_tool": used_tool}
        except Exception as exc:  # noqa: BLE001 - never break the panel
            logger.warning("assistant LLM path failed (%s); using deterministic router", exc)

    return {"text": _route(question, ctx), "evidence": ctx["evidence"], "used_tool": used_tool}

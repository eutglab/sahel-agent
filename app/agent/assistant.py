"""Ask the Agent — a conversational panel over the current analysis.

Not a generic chatbot: it never invents facts. Two explicit states:

- ``pre_analysis`` (no result yet): answers general product questions
  (what it analyzes, how it works, what confidence means) and — if asked
  about a specific field — says plainly that no analysis has run yet.
  Never invents a risk level, observation or recommendation.
- ``analysis_ready`` (a result exists): answers from the SAME structured
  result the main pipeline already produced (risk, recommendation,
  evidence, limitations), and — the one genuinely agentic step — can
  trigger the existing ``search_web`` tool itself, live, if a question
  needs evidence that wasn't already fetched (because risk was low and
  the pipeline skipped it). No new tool is added; this only calls tools
  already in the registry.

Mirrors the main agent's own two-level honesty: a deterministic keyword
router by default (same spirit as the L2 planner), and a real LLM — grounded
on this same structured context, never free-associating — only when one is
actually configured and online (same spirit as L1). Any LLM failure falls
back to the router silently; the panel never breaks, in either state.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.core.schemas import AgentInput, AgentResult
from app.llm.factory import get_llm_client
from app.tools.registry import get_registry

logger = get_logger("sahel.assistant")

# Post-analysis: shortcuts into the current result. Pre-analysis: shortcuts
# into general product knowledge. Both are routing hints, not separate
# chatbot systems — free text hits the exact same router either way.
SUGGESTED_QUESTIONS = [
    "Why is the risk moderate?",
    "What should I do first?",
    "Show me the evidence.",
]
GENERAL_SUGGESTED_QUESTIONS = [
    "What can you analyze?",
    "How does SAHEL Agent work?",
    "What does confidence mean?",
]

_SYSTEM_READY = (
    "You are the conversational interface of SAHEL Agent, an environmental "
    "decision-support tool. Answer ONLY using the STRUCTURED ANALYSIS JSON given "
    "below — never invent numbers, sources or facts absent from it. Be concise: "
    "2-4 sentences, plain language, no chain-of-thought. If the analysis doesn't "
    "cover what's asked, say so plainly rather than guessing."
)
_SYSTEM_PRE = (
    "You are the conversational interface of SAHEL Agent, an environmental "
    "decision-support tool. No field has been analyzed yet in this session. "
    "Answer general questions about what the product does, how it works, what "
    "inputs help, and what confidence/evidence/risk levels mean — 2-4 sentences, "
    "plain language. If the user asks about a specific field's current risk, "
    "observations or recommendations, say plainly that no analysis has run yet "
    "and suggest pressing Analyze Field — never invent field-specific data."
)

_FIELD_SPECIFIC_HINTS = (
    "my field", "risk in my", "is it moderate", "is it high", "current risk",
    "what is the risk", "why is the risk", "why is risk", "moderate risk", "high risk",
    "recommend", "recommendation", "the risk is", "is my field", "in my crop",
)


def _route_pre_analysis(question: str) -> str:
    """analysis_ready == False: general product Q&A, never field-specific data."""
    q = question.lower()

    if any(k in q for k in ("what can you analyze", "what do you analyze", "what can you do")):
        return (
            "I assess environmental and agricultural risk from a field photo, sensor "
            "readings (temperature, soil moisture, air humidity, rainfall) and a location. "
            "I estimate water stress, heat stress and environmental risk, then recommend "
            "actions. Press Analyze Field with whatever inputs you have — none are required."
        )

    if "how does" in q or "how do you work" in q or "how it works" in q:
        return (
            "I look at whichever inputs you give me, run the relevant checks (image, sensors, "
            "weather), combine them into one risk assessment with a cross-check between "
            "sources, and — if the risk looks elevated — search for external evidence before "
            "recommending actions."
        )

    if any(k in q for k in ("what data", "what should i provide", "what input", "what do i need")):
        return (
            "Any of these helps, and none are strictly required: a field or plant photo, "
            "sensor readings (temperature, soil moisture, humidity, rainfall), a growth stage, "
            "and a location. More inputs generally raise confidence."
        )

    if "confidence" in q:
        return (
            "Confidence reflects how much the available sources agree. It drops when inputs "
            "are missing or contradictory, and rises when image, sensor and weather signals "
            "converge on the same conclusion."
        )

    if any(k in q for k in ("evidence", "exa", "source")):
        return (
            "When a risk looks moderate or high, I search the web (via Exa) for relevant "
            "advisories and cite them in the result. I haven't checked anything yet since no "
            "field has been analyzed."
        )

    if any(k in q for k in ("risk level", "how do you calculate", "risk score")):
        return (
            "Risk splits into water stress, heat stress and environmental risk, each scored "
            "from the evidence available, then combined into one overall level — low, "
            "moderate or high."
        )

    if any(k in q for k in _FIELD_SPECIFIC_HINTS):
        return (
            "I don't have a field assessment yet. Run an analysis first and I can explain "
            "the risk, its main drivers, the evidence, and the recommended actions."
        )

    return (
        "I'm the SAHEL Agent. Ask me what I can analyze, how the assessment works, or what "
        "data helps — or press Analyze Field and ask me about the result."
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


def _route_ready(question: str, ctx: Dict[str, Any]) -> str:
    """analysis_ready == True: answer from the current, already-computed result."""
    q = question.lower()
    ev_note = ""
    if ctx["evidence"]:
        src = "live web search (Exa)" if ctx["evidence_source"] == "exa" else "offline sample data"
        ev_note = f" I also checked {len(ctx['evidence'])} external source(s) via {src}."

    if any(k in q for k in ("why", "reason", "cause", "driver")):
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

    if "water" in q:
        sub = ctx["water_stress"]
        drivers = ", ".join(sub.get("drivers", [])[:2]) or "no specific driver logged"
        return f"Water stress is {sub.get('level', 'unknown')}. {drivers}.{ev_note}"

    if "heat" in q or "temperature" in q:
        sub = ctx["heat_stress"]
        drivers = ", ".join(sub.get("drivers", [])[:2]) or "no specific driver logged"
        return f"Heat stress is {sub.get('level', 'unknown')}. {drivers}.{ev_note}"

    if any(k in q for k in ("evidence", "source", "check", "danger", "safe", "confirm")):
        if ctx["evidence"]:
            src = "live web search (Exa)" if ctx["evidence_source"] == "exa" else "offline sample data"
            names = "; ".join(e.get("title", "source") for e in ctx["evidence"][:3])
            return f"Yes — {len(ctx['evidence'])} source(s) via {src}: {names}."
        return (
            f"Risk was assessed as {ctx['combined_risk']}, so no external evidence lookup "
            "was triggered for this analysis."
        )

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


def needs_live_evidence(question: str, result: Optional[AgentResult]) -> bool:
    """UI helper: true when this question would trigger a live search_web call,
    so the caller can show a specific 'checking evidence' activity indicator."""
    if result is None:
        return False
    evidence_already = bool((result.recommendation or {}).get("evidence"))
    if evidence_already:
        return False
    return any(k in question.lower() for k in ("evidence", "source", "danger", "safe", "confirm"))


_LANG_NAMES = {"fr": "French", "bm": "French (Bambara is not reliably supported — use French)"}


def answer(
    question: str,
    result: Optional[AgentResult],
    agent_input: Optional[AgentInput] = None,
    lang: str = "en",
) -> Dict[str, Any]:
    """Answer ``question``. Never raises, never invents field data that wasn't
    actually produced by the pipeline.

    ``lang`` only affects the real-LLM path (asked to respond in that
    language, still grounded on the same structured data). The deterministic
    router's templated text is English-only by design — see docs/i18n.md —
    the UI discloses this rather than mixing partial translations into a
    single sentence.
    """
    lang_instruction = f" Respond in {_LANG_NAMES[lang]}." if lang in _LANG_NAMES else ""

    if result is None:
        client = get_llm_client()
        if not client.is_mock and not settings.offline_first:
            try:
                resp = client.complete(_SYSTEM_PRE + lang_instruction, question, max_tokens=200)
                if resp.text.strip():
                    return {
                        "text": resp.text.strip(), "evidence": [], "used_tool": None,
                        "source": "llm", "provider": client.name,
                    }
            except Exception as exc:  # noqa: BLE001 - never break the panel
                logger.warning("assistant LLM path failed (%s); using deterministic router", exc)
        return {
            "text": _route_pre_analysis(question), "evidence": [], "used_tool": None,
            "source": "router", "provider": None,
        }

    ctx = _context(result)
    used_tool = None
    if needs_live_evidence(question, result):
        fetched = _maybe_fetch_evidence(ctx, agent_input)
        if fetched:
            ctx["evidence"] = fetched
            ctx["evidence_source"] = "exa"
            used_tool = "search_web"

    client = get_llm_client()
    if not client.is_mock and not settings.offline_first:
        try:
            prompt = "STRUCTURED ANALYSIS:\n" + json.dumps(ctx, default=str)[:5000] + f"\n\nQUESTION: {question}"
            resp = client.complete(_SYSTEM_READY + lang_instruction, prompt, max_tokens=250)
            if resp.text.strip():
                return {
                    "text": resp.text.strip(), "evidence": ctx["evidence"], "used_tool": used_tool,
                    "source": "llm", "provider": client.name,
                }
        except Exception as exc:  # noqa: BLE001 - never break the panel
            logger.warning("assistant LLM path failed (%s); using deterministic router", exc)

    return {
        "text": _route_ready(question, ctx), "evidence": ctx["evidence"], "used_tool": used_tool,
        "source": "router", "provider": None,
    }

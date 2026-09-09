"""SAHEL Agent — Streamlit interface.

Run:  streamlit run ui/streamlit_app.py
Works with zero API keys (DEMO_MODE / mock LLM by default).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agent.agent import SahelAgent  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.schemas import AgentInput, GrowthStage, Location, SensorReadings  # noqa: E402
from app.core.security import validate_image_upload  # noqa: E402
from app.data.demo_data import get_scenario, list_scenarios, load_scenario_image  # noqa: E402

st.set_page_config(page_title="SAHEL Agent", page_icon="🌍", layout="wide")

_CSS = """
<style>
.block-container {padding-top: 2rem; max-width: 1150px;}
h1, h2, h3 {letter-spacing: -0.01em;}
.sahel-sub {color: #6b7280; font-size: 0.95rem; margin-top: -0.6rem;}
.trace-line {font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.86rem; padding: 1px 0;}
.badge {display:inline-block; padding: 2px 9px; border-radius: 999px; font-size: 0.74rem;
        font-weight: 600; margin-right: 6px;}
.badge-low {background:#dcfce7; color:#166534;}
.badge-moderate {background:#fef9c3; color:#854d0e;}
.badge-medium {background:#fef9c3; color:#854d0e;}
.badge-high {background:#fee2e2; color:#991b1b;}
.badge-unknown {background:#e5e7eb; color:#374151;}
.small {color:#6b7280; font-size:0.82rem;}
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

# --- DEMO_JUDGE_MODE: preload the strongest scenario once, zero clicks to set up.
if settings.demo_judge_mode and "_judge_init" not in st.session_state:
    _scn = get_scenario(settings.demo_judge_scenario) or (list_scenarios() or [None])[0]
    if _scn:
        st.session_state["loaded"] = _scn
    st.session_state["_judge_init"] = True


def _badge(level: str) -> str:
    lvl = (level or "unknown").lower()
    cls = {"low": "badge-low", "moderate": "badge-moderate", "medium": "badge-medium",
           "high": "badge-high"}.get(lvl, "badge-unknown")
    return f'<span class="badge {cls}">{lvl.upper()}</span>'


# --------------------------------------------------------------------------- #
# Sidebar — environment + demo loader
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.subheader("Runtime")
    cfg = settings.public_summary()
    st.markdown(
        f"**Environment:** `{cfg['environment']}`  \n"
        f"**Demo mode:** `{cfg['demo_mode']}`  \n"
        f"**LLM:** `{cfg['llm_provider']}`  \n"
        f"**Weather:** `{cfg['weather_provider']}` · **Vision:** `{cfg['vision_provider']}`  \n"
        f"**Recommendation:** `{cfg['recommendation_provider']}`"
    )
    st.caption("Runs fully offline with mock LLM + local providers. No keys required.")
    st.divider()

    st.subheader("Load demo scenario")
    scenarios = list_scenarios()
    labels = ["— none —"] + [s.get("title", s["id"]) for s in scenarios]
    picked = st.selectbox("Scenario", labels, index=0, label_visibility="collapsed")
    col_a, col_b = st.columns(2)
    if col_a.button("Load", width="stretch") and picked != "— none —":
        scn = scenarios[labels.index(picked) - 1]
        st.session_state["loaded"] = scn
        st.session_state.pop("result", None)
        st.rerun()
    if col_b.button("Reset", width="stretch"):
        for k in ("loaded", "result"):
            st.session_state.pop(k, None)
        st.rerun()

    if "loaded" in st.session_state:
        st.success(f"Loaded: {st.session_state['loaded'].get('title', st.session_state['loaded']['id'])}")
        st.caption(st.session_state["loaded"].get("description", ""))


loaded = st.session_state.get("loaded", {})
ls = loaded.get("sensors", {}) if loaded else {}
ll = loaded.get("location", {}) if loaded else {}

# --------------------------------------------------------------------------- #
# Header + input
# --------------------------------------------------------------------------- #
st.title("SAHEL Agent")
st.markdown('<p class="sahel-sub">Multimodal AI Agent for Environmental &amp; Agricultural Intelligence</p>',
            unsafe_allow_html=True)
if settings.demo_judge_mode:
    st.info(f"**Judge demo mode** — scenario *{loaded.get('title', settings.demo_judge_scenario)}* "
            f"is preloaded. Press **ANALYZE** to run the agent.")
st.write("")

left, right = st.columns([1, 1])
with left:
    st.markdown("### Input")
    up = st.file_uploader("Plant / field image (optional)", type=["jpg", "jpeg", "png", "webp"])
    image_bytes = None
    if up is not None:
        image_bytes = up.read()
    elif loaded and loaded.get("image"):
        image_bytes = load_scenario_image(loaded)
    if image_bytes:
        try:
            validate_image_upload(image_bytes)
            st.image(image_bytes, caption="input image", width=260)
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Image rejected: {exc}")
            image_bytes = None

    def _pre(key):
        v = ls.get(key)
        return float(v) if v is not None else None

    c1, c2 = st.columns(2)
    temp = c1.number_input("Temperature (°C)", value=_pre("temperature_c"),
                           min_value=-30.0, max_value=60.0, step=0.5, format="%.1f", placeholder="—")
    soil = c2.number_input("Soil moisture (%)", value=_pre("soil_moisture_pct"),
                           min_value=0.0, max_value=100.0, step=1.0, placeholder="—")
    c3, c4 = st.columns(2)
    airh = c3.number_input("Air humidity (%)", value=_pre("air_humidity_pct"),
                           min_value=0.0, max_value=100.0, step=1.0, placeholder="—")
    rain = c4.number_input("Rainfall (mm)", value=_pre("rainfall_mm"),
                           min_value=0.0, max_value=2000.0, step=0.5, placeholder="—")

    stages = [g.value for g in GrowthStage]
    stage_default = ls.get("growth_stage", "unknown")
    stage = st.selectbox("Growth stage", stages, index=stages.index(stage_default) if stage_default in stages else stages.index("unknown"))

    loc_label = st.text_input("Location label", value=ll.get("label") or "")
    c5, c6 = st.columns(2)
    lat = c5.number_input("Latitude", value=float(ll["latitude"]) if ll.get("latitude") is not None else None,
                          min_value=-90.0, max_value=90.0, format="%.4f", placeholder="—")
    lon = c6.number_input("Longitude", value=float(ll["longitude"]) if ll.get("longitude") is not None else None,
                          min_value=-180.0, max_value=180.0, format="%.4f", placeholder="—")

    text_context = st.text_area("Context (optional)", value=loaded.get("text_context", "") if loaded else "", height=70)

    analyze = st.button("ANALYZE", type="primary", width="stretch")

# --------------------------------------------------------------------------- #
# Run the agent
# --------------------------------------------------------------------------- #
if analyze:
    agent_input = AgentInput(
        text_context=text_context or "",
        image_bytes=image_bytes,
        image_name=(up.name if up is not None else loaded.get("image")),
        sensors=SensorReadings(
            temperature_c=temp,
            soil_moisture_pct=soil,
            air_humidity_pct=airh,
            rainfall_mm=rain,
            growth_stage=stage,
        ),
        location=Location(label=(loc_label.strip()[:120] or None), latitude=lat, longitude=lon),
        scenario_id=loaded.get("id") if loaded else None,
    )
    with right:
        st.markdown("### Agent activity")
        holder = st.empty()
        with st.spinner("Agent working…"):
            t0 = time.time()
            result = SahelAgent().analyze(agent_input)
        lines = result.trace.as_lines()
        holder.markdown(
            "\n".join(f'<div class="trace-line">{ln}</div>' for ln in lines),
            unsafe_allow_html=True,
        )
    st.session_state["result"] = result

# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
result = st.session_state.get("result")
if result is not None:
    obs = result.observation
    risk = obs.risk or {}
    rec = result.recommendation or {}
    combined = (risk.get("combined_risk") or {})

    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Reasoning mode", result.reasoning_mode)
    m2.metric("Tools used", len(result.tools_used))
    m3.metric("Execution", f"{result.execution_ms:.0f} ms")
    m4.metric("Confidence", f"{float(rec.get('confidence', risk.get('confidence', 0)) or 0):.0%}")

    if result.degraded:
        st.warning("Ran in degraded mode — see errors in Run details. A fallback level was used.")

    st.markdown("## Situation")
    st.markdown(
        f"{_badge(combined.get('level', 'unknown'))} {result.situation_line()}",
        unsafe_allow_html=True,
    )
    for note in obs.notes:
        st.markdown(f'<span class="small">• {note}</span>', unsafe_allow_html=True)

    tab_obs, tab_env, tab_risk, tab_rec, tab_conf, tab_run = st.tabs(
        ["Visual observations", "Environmental analysis", "Risk assessment",
         "Recommendations", "Confidence & limitations", "Run details"]
    )

    with tab_obs:
        v = obs.vision
        if not v:
            st.info("No image was provided, so no visual analysis was run.")
        else:
            st.caption(f"method: {v.get('method', 'n/a')} · confidence {float(v.get('confidence', 0)):.0%}")
            st.markdown("**Observations**")
            for o in v.get("observations", []):
                st.markdown(f"- {o}")
            if v.get("possible_signs"):
                st.markdown("**Possible signs** (not a diagnosis)")
                for s in v["possible_signs"]:
                    st.markdown(f"- {s}")
            st.markdown("**Limitations**")
            for lm in v.get("limitations", []):
                st.markdown(f'<span class="small">- {lm}</span>', unsafe_allow_html=True)

    with tab_env:
        s = obs.sensors
        if not s:
            st.info("No sensor readings were provided.")
        else:
            st.caption(f"method: {s.get('method', '')}")
            st.markdown(f"**Sensor risk level:** {_badge(s.get('risk_level', 'unknown'))}", unsafe_allow_html=True)
            st.caption("Single-tool view from sensor thresholds alone. The multimodal "
                       "**combined risk** (Risk assessment tab) weights this together with image and weather.")
            import pandas as pd

            df = pd.DataFrame(s.get("indicators", []))
            if not df.empty:
                st.dataframe(df, width="stretch", hide_index=True)
            if s.get("anomalies"):
                st.markdown("**Anomalies**")
                for a in s["anomalies"]:
                    st.markdown(f"- {a}")
            st.markdown("**Explanation**")
            for e in s.get("explanation", []):
                st.markdown(f"- {e}")
        wx = obs.weather
        if wx:
            st.markdown(f"**Weather** — source: `{wx.get('source', 'n/a')}`")
            st.markdown(
                f"- temperature: {wx.get('temperature_c')} °C · humidity: {wx.get('humidity_pct')} % "
                f"· rain prob: {wx.get('rain_probability')} %"
            )
            if wx.get("note"):
                st.markdown(f'<span class="small">{wx["note"]}</span>', unsafe_allow_html=True)

    with tab_risk:
        if not risk:
            st.info("Risk not computed.")
        else:
            for key in ("water_stress", "heat_stress", "environmental", "combined_risk"):
                sub = risk.get(key) or {}
                st.markdown(
                    f"**{key.replace('_', ' ').title()}** {_badge(sub.get('level'))} "
                    f"<span class='small'>score {float(sub.get('score', 0)):.2f}</span>",
                    unsafe_allow_html=True,
                )
                for d in sub.get("drivers", []):
                    st.markdown(f'<span class="small">&nbsp;&nbsp;— {d}</span>', unsafe_allow_html=True)
            xc = risk.get("cross_check", {})
            st.markdown("**Cross-check**")
            for c in xc.get("converging_evidence", []) or ["(no strong converging evidence)"]:
                st.markdown(f"- ✅ {c}")
            for c in xc.get("diverging_evidence", []):
                st.markdown(f"- ⚠️ {c}")
            st.markdown(f'<span class="small">{risk.get("disclaimer", "")}</span>', unsafe_allow_html=True)

    with tab_rec:
        if not rec:
            st.info("No recommendation produced.")
        else:
            st.markdown(f"**Priority:** {_badge(rec.get('priority'))}", unsafe_allow_html=True)
            st.markdown(f"**Main finding:** {rec.get('main_finding', '')}")
            st.markdown("**Recommended actions**")
            for a in rec.get("recommended_actions", []):
                st.markdown(f"- {a}")
            st.markdown("**Monitoring**")
            for a in rec.get("monitoring_actions", []):
                st.markdown(f"- {a}")
            if rec.get("warnings"):
                st.markdown("**Warnings**")
                for w in rec["warnings"]:
                    st.markdown(f"- {w}")
            st.caption(f"method: {rec.get('method', '')}")

    with tab_conf:
        st.metric("Overall confidence", f"{float(rec.get('confidence', risk.get('confidence', 0)) or 0):.0%}")
        st.markdown("**Limitations**")
        for lm in (rec.get("limitations") or []):
            st.markdown(f"- {lm}")
        if result.errors:
            st.markdown("**Errors / degradations**")
            for e in result.errors:
                st.markdown(f"- {e}")

    with tab_run:
        st.markdown(f"**Scenario:** `{result.scenario_id}` · **mode:** `{result.reasoning_mode}`")
        rows = []
        for call in result.trace.tool_calls:
            rows.append({
                "tool": call.tool_name,
                "provider": call.provider_used,
                "ok": call.success,
                "ms": call.duration_ms,
                "note": call.source_note or call.error or "",
            })
        if rows:
            import pandas as pd

            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        st.markdown("**Trace**")
        st.code("\n".join(result.trace.as_lines()), language="text")
        with st.expander("Raw result JSON"):
            st.json(result.model_dump(exclude={"trace"}))
else:
    with right:
        st.markdown("### Agent activity")
        st.info("Load a demo scenario or fill the form, then press **ANALYZE**.")

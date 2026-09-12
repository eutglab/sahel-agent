"""SAHEL Agent — Streamlit interface.

Run:  streamlit run ui/streamlit_app.py
Works with zero API keys (DEMO_MODE / mock LLM by default).

Hierarchy: INPUT -> ANALYSIS -> RISK -> WHY -> ACTION -> EVIDENCE, with every
technical detail (provider, reasoning level, raw trace, tool timings) moved
behind "Technical Details" rather than shown up front. See docs/agent_design.md
for what actually produces each number shown here — this file only renders it.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agent.agent import SahelAgent  # noqa: E402
from app.agent.assistant import SUGGESTED_QUESTIONS, answer as assistant_answer  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.i18n import LANGUAGES, PARTIAL_NOTICE, t  # noqa: E402
from app.core.schemas import AgentInput, GrowthStage, Location, SensorReadings  # noqa: E402
from app.core.security import validate_image_upload  # noqa: E402
from app.data.demo_data import get_scenario, list_scenarios, load_scenario_image  # noqa: E402

st.set_page_config(page_title="SAHEL Agent", page_icon="🌍", layout="wide")


def _css(theme: str) -> str:
    """Force a consistent light/dark look regardless of the browser's own
    Streamlit theme setting — driven by the toggle button, not guessed."""
    if theme == "dark":
        bg, bg2, text, sub, border = "#0e1117", "#1a1d24", "#e5e7eb", "#9ca3af", "#30343c"
        hero_bg = "#171b23"
    else:
        bg, bg2, text, sub, border = "#ffffff", "#f8fafc", "#111827", "#6b7280", "#e5e7eb"
        hero_bg = "#f8fafc"
    return f"""
    <style>
    :root {{ --background-color: {bg}; --secondary-background-color: {bg2}; --text-color: {text}; }}
    .stApp {{ background-color: {bg} !important; color: {text} !important; }}
    [data-testid="stSidebar"] {{ background-color: {bg2} !important; }}
    [data-testid="stHeader"] {{ background-color: transparent !important; }}
    .stApp, .stApp p, .stApp label, .stApp span, .stApp li {{ color: {text}; }}
    .block-container {{padding-top: 1.6rem; max-width: 1100px;}}
    h1, h2, h3 {{letter-spacing: -0.01em;}}
    .sahel-sub {{color: {sub} !important; font-size: 1.02rem; margin-top: -0.5rem;}}
    .trace-line {{font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.82rem; padding: 1px 0; color: {sub};}}
    .badge {{display:inline-block; padding: 2px 9px; border-radius: 999px; font-size: 0.74rem;
            font-weight: 600; margin-right: 6px;}}
    .badge-low {{background:#dcfce7; color:#166534;}}
    .badge-moderate {{background:#fef9c3; color:#854d0e;}}
    .badge-medium {{background:#fef9c3; color:#854d0e;}}
    .badge-high {{background:#fee2e2; color:#991b1b;}}
    .badge-unknown {{background:#e5e7eb; color:#374151;}}
    .small {{color: {sub} !important; font-size:0.82rem;}}
    hr {{border-color: {border} !important;}}

    /* --- risk hero ------------------------------------------------------ */
    .risk-hero {{background:{hero_bg}; border:1px solid {border}; border-radius:12px;
                 padding:20px 24px; margin: 10px 0 16px;}}
    .risk-eyebrow {{font-size:0.72rem; letter-spacing:0.08em; color:{sub}; font-weight:600; margin-bottom:8px;}}
    .risk-badge-big {{font-size:1.9rem; font-weight:700; letter-spacing:-0.01em; display:inline-block; margin-right:14px;}}
    .risk-badge-big.low {{color:#166534;}}
    .risk-badge-big.moderate, .risk-badge-big.medium {{color:#854d0e;}}
    .risk-badge-big.high {{color:#991b1b;}}
    .risk-badge-big.unknown {{color:{sub};}}
    .risk-situation {{color:{text}; font-size:0.98rem; margin-top:6px;}}
    .risk-driver {{font-size:1.02rem; font-weight:600; margin-top:10px; color:{text};}}

    /* --- indicators ------------------------------------------------------ */
    .indicator {{border:1px solid {border}; border-radius:10px; padding:10px 14px; text-align:left;}}
    .indicator .ind-label {{font-size:0.78rem; color:{sub}; margin-bottom:4px;}}

    /* --- checklist -------------------------------------------------------- */
    .checklist {{font-size:0.86rem; line-height:1.9; color:{text};}}
    .checklist .ok {{color:#166534; font-weight:600;}}
    .checklist .skip {{color:{sub};}}

    /* --- chat --------------------------------------------------------------- */
    .chat-bubble-user {{background:{hero_bg}; border:1px solid {border}; border-radius:10px 10px 2px 10px;
                         padding:8px 12px; margin:4px 0; font-size:0.9rem;}}
    .chat-bubble-agent {{background:transparent; border:1px solid {border}; border-radius:10px 10px 10px 2px;
                          padding:8px 12px; margin:4px 0 12px; font-size:0.9rem;}}
    </style>
    """


st.session_state.setdefault("theme", "light")
st.markdown(_css(st.session_state["theme"]), unsafe_allow_html=True)

# --- DEMO_JUDGE_MODE: preload the strongest scenario once, zero clicks to set up.
# Judges always see English regardless of any language previously picked in this
# session — the product's default, judged language is English (see PARTIAL_NOTICE
# for the disclosed scope of French/Bambara support).
if settings.demo_judge_mode and "_judge_init" not in st.session_state:
    _scn = get_scenario(settings.demo_judge_scenario) or (list_scenarios() or [None])[0]
    if _scn:
        st.session_state["loaded"] = _scn
    st.session_state["_judge_init"] = True
    st.session_state["lang"] = "en"

st.session_state.setdefault("lang", "en")
st.session_state.setdefault("chat_history", [])
st.session_state.setdefault("show_details", False)
st.session_state.setdefault("show_evidence", False)

# --- Header bar: theme + language + Ask the Agent, all secondary to the ------
# --- product itself — none of this competes visually with Analyze Field. ----
_bar_l, _bar_theme, _bar_lang, _bar_chat = st.columns([4.2, 1, 1, 1.6])
with _bar_theme:
    _is_dark = st.session_state["theme"] == "dark"
    if st.button("☀️" if _is_dark else "🌙", width="stretch", key="_theme_toggle",
                 help="Toggle light/dark"):
        st.session_state["theme"] = "light" if _is_dark else "dark"
        st.rerun()
with _bar_lang:
    _codes = list(LANGUAGES)
    _picked = st.selectbox(
        "Language", _codes, index=_codes.index(st.session_state["lang"]),
        format_func=lambda c: LANGUAGES[c], label_visibility="collapsed", key="_lang_picker",
    )
    if _picked != st.session_state["lang"]:
        st.session_state["lang"] = _picked
        st.rerun()
lang = st.session_state["lang"]
_chat_slot = _bar_chat  # button rendered below, once `result` is known


def _t_or(key: str, default: str) -> str:
    val = t(key, lang)
    return val if val != key else default


def _badge(level: str) -> str:
    lvl = (level or "unknown").lower()
    cls = {"low": "badge-low", "moderate": "badge-moderate", "medium": "badge-medium",
           "high": "badge-high"}.get(lvl, "badge-unknown")
    label = t(f"badge_{lvl}", lang) if f"badge_{lvl}" in _BADGE_KEYS else lvl.upper()
    return f'<span class="badge {cls}">{label}</span>'


_BADGE_KEYS = {"badge_low", "badge_moderate", "badge_medium", "badge_high", "badge_unknown"}

_DRIVER_KEYS = {"water_stress": "driver_water", "heat_stress": "driver_heat", "environmental": "driver_env"}
_INDICATOR_KEYS = {"water_stress": "indicator_water", "heat_stress": "indicator_heat", "environmental": "indicator_env"}


def _dominant_driver(risk: dict) -> str | None:
    best_key, best_score = None, -1.0
    for key in ("water_stress", "heat_stress", "environmental"):
        sub = risk.get(key) or {}
        if sub.get("level") in {"moderate", "high"} and float(sub.get("score", 0)) > best_score:
            best_key, best_score = key, float(sub.get("score", 0))
    return best_key


def _why_reasons(risk: dict, max_n: int = 4) -> list[str]:
    reasons: list[str] = []
    for key in ("water_stress", "heat_stress", "environmental"):
        sub = risk.get(key) or {}
        if sub.get("level") in {"moderate", "high"}:
            reasons.extend(sub.get("drivers", []))
    for c in (risk.get("cross_check") or {}).get("converging_evidence", []):
        reasons.append(c)
    seen, out = set(), []
    for r in reasons:
        if r not in seen:
            out.append(r)
            seen.add(r)
        if len(out) >= max_n:
            break
    return out


def _evidence_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "") or url
    except Exception:  # noqa: BLE001
        return url


@st.dialog(t("chat_title", lang))
def _ask_agent_dialog(result, agent_input):
    st.caption(t("chat_subtitle", lang))
    if result is None:
        st.info(t("chat_empty", lang))
        return

    for role, text_ in st.session_state["chat_history"]:
        cls = "chat-bubble-user" if role == "user" else "chat-bubble-agent"
        st.markdown(f'<div class="{cls}">{text_}</div>', unsafe_allow_html=True)

    sug_cols = st.columns(len(SUGGESTED_QUESTIONS))
    for i, q in enumerate(SUGGESTED_QUESTIONS):
        if sug_cols[i].button(q, key=f"_sugg_{i}", width="stretch"):
            _ask(q, result, agent_input)
            st.rerun()

    q_col, send_col = st.columns([5, 1])
    q_text = q_col.text_input(t("chat_placeholder", lang), key="_chat_input", label_visibility="collapsed",
                               placeholder=t("chat_placeholder", lang))
    if send_col.button(t("chat_send", lang), width="stretch") and q_text.strip():
        _ask(q_text.strip(), result, agent_input)
        st.rerun()

    if st.button(t("chat_voice", lang), key="_chat_voice"):
        st.caption(t("chat_voice_note", lang))


def _ask(question: str, result, agent_input) -> None:
    st.session_state["chat_history"].append(("user", question))
    resp = assistant_answer(question, result, agent_input)
    st.session_state["chat_history"].append(("agent", resp["text"]))


# --------------------------------------------------------------------------- #
# Sidebar — demo loader up front, technical config tucked away
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.subheader(t("sidebar_load_scenario", lang))
    scenarios = list_scenarios()
    labels = ["— none —"] + [s.get("title", s["id"]) for s in scenarios]
    picked = st.selectbox("Scenario", labels, index=0, label_visibility="collapsed")
    col_a, col_b = st.columns(2)
    if col_a.button(t("load", lang), width="stretch") and picked != "— none —":
        scn = scenarios[labels.index(picked) - 1]
        st.session_state["loaded"] = scn
        st.session_state.pop("result", None)
        st.session_state["chat_history"] = []
        st.rerun()
    if col_b.button(t("reset", lang), width="stretch"):
        for k in ("loaded", "result", "chat_history"):
            st.session_state.pop(k, None)
        st.rerun()

    if "loaded" in st.session_state:
        st.success(f"Loaded: {st.session_state['loaded'].get('title', st.session_state['loaded']['id'])}")
        st.caption(st.session_state["loaded"].get("description", ""))

    st.divider()
    with st.expander(t("sidebar_runtime", lang)):
        cfg = settings.public_summary()
        st.markdown(
            f"**Environment:** `{cfg['environment']}`  \n"
            f"**Demo mode:** `{cfg['demo_mode']}`  \n"
            f"**LLM:** `{cfg['llm_provider']}`  \n"
            f"**Weather:** `{cfg['weather_provider']}` · **Vision:** `{cfg['vision_provider']}`  \n"
            f"**Recommendation:** `{cfg['recommendation_provider']}` · **Web search:** `{cfg['web_search_provider']}`"
        )
        st.caption(t("offline_caption", lang))


loaded = st.session_state.get("loaded", {})
ls = loaded.get("sensors", {}) if loaded else {}
ll = loaded.get("location", {}) if loaded else {}

# --------------------------------------------------------------------------- #
# Header + input
# --------------------------------------------------------------------------- #
st.title(t("app_title", lang))
st.markdown(f'<p class="sahel-sub">{t("app_tagline", lang)}</p>', unsafe_allow_html=True)
if settings.demo_judge_mode:
    st.info(t("judge_mode_banner", lang, scenario=loaded.get("title", settings.demo_judge_scenario)))

_existing_result = st.session_state.get("result")
with _chat_slot:
    if st.button(t("chat_button", lang), width="stretch", key="_open_chat"):
        _ask_agent_dialog(_existing_result, st.session_state.get("last_agent_input"))

st.write("")

left, right = st.columns([1, 1])
with left:
    st.markdown(f"### {t('input_header', lang)}")
    up = st.file_uploader(t("image_uploader", lang), type=["jpg", "jpeg", "png", "webp"])
    image_bytes = None
    if up is not None:
        image_bytes = up.read()
    elif loaded and loaded.get("image"):
        image_bytes = load_scenario_image(loaded)
    if image_bytes:
        try:
            validate_image_upload(image_bytes)
            st.image(image_bytes, caption="input image", width=220)
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Image rejected: {exc}")
            image_bytes = None

    def _pre(key):
        v = ls.get(key)
        return float(v) if v is not None else None

    st.markdown(f"**{t('sensor_readings_header', lang)}**")
    c1, c2 = st.columns(2)
    temp = c1.number_input(t("temperature", lang), value=_pre("temperature_c"),
                           min_value=-30.0, max_value=60.0, step=0.5, format="%.1f", placeholder="—")
    soil = c2.number_input(t("soil_moisture", lang), value=_pre("soil_moisture_pct"),
                           min_value=0.0, max_value=100.0, step=1.0, placeholder="—")
    c3, c4 = st.columns(2)
    airh = c3.number_input(t("air_humidity", lang), value=_pre("air_humidity_pct"),
                           min_value=0.0, max_value=100.0, step=1.0, placeholder="—")
    rain = c4.number_input(t("rainfall", lang), value=_pre("rainfall_mm"),
                           min_value=0.0, max_value=2000.0, step=0.5, placeholder="—")

    st.markdown(f"**{t('location_header', lang)}**")
    loc_label = st.text_input(t("location_label", lang), value=ll.get("label") or "", label_visibility="collapsed",
                              placeholder=t("location_label", lang))

    with st.expander(t("advanced_input", lang)):
        stages = [g.value for g in GrowthStage]
        stage_default = ls.get("growth_stage", "unknown")
        stage = st.selectbox(t("growth_stage", lang), stages,
                             index=stages.index(stage_default) if stage_default in stages else stages.index("unknown"))
        c5, c6 = st.columns(2)
        lat = c5.number_input(t("latitude", lang), value=float(ll["latitude"]) if ll.get("latitude") is not None else None,
                              min_value=-90.0, max_value=90.0, format="%.4f", placeholder="—")
        lon = c6.number_input(t("longitude", lang), value=float(ll["longitude"]) if ll.get("longitude") is not None else None,
                              min_value=-180.0, max_value=180.0, format="%.4f", placeholder="—")
        text_context = st.text_area(t("context_optional", lang), value=loaded.get("text_context", "") if loaded else "", height=70)

    analyze = st.button(t("analyze_button", lang), type="primary", width="stretch")

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
        st.markdown(f"### {t('agent_activity', lang)}")
        with st.spinner(t("agent_working", lang)):
            result = SahelAgent().analyze(agent_input)
    st.session_state["result"] = result
    st.session_state["last_agent_input"] = agent_input
    st.session_state["chat_history"] = []
    st.session_state["show_details"] = False
    st.session_state["show_evidence"] = False

# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
result = st.session_state.get("result")
if result is not None:
    obs = result.observation
    risk = obs.risk or {}
    rec = result.recommendation or {}
    combined = (risk.get("combined_risk") or {})
    combined_level = (combined.get("level") or "unknown").lower()

    if result.degraded:
        st.warning("Ran in degraded mode — see errors in Technical Details. A fallback level was used.")

    # --- 1. FIELD RISK ASSESSMENT ------------------------------------------- #
    driver_key = _dominant_driver(risk)
    driver_line = (
        t("main_driver_tmpl", lang, driver=t(_DRIVER_KEYS[driver_key], lang))
        if driver_key else t("no_driver", lang)
    )
    st.markdown(
        f"""<div class="risk-hero">
            <div class="risk-eyebrow">{t('risk_hero_label', lang)}</div>
            <span class="risk-badge-big {combined_level}">{t(f'badge_{combined_level}', lang) if f'badge_{combined_level}' in _BADGE_KEYS else combined_level.upper()}</span>
            <div class="risk-situation">{result.situation_line()}</div>
            <div class="risk-driver">{driver_line}</div>
        </div>""",
        unsafe_allow_html=True,
    )

    # --- 2. three compact indicators ---------------------------------------- #
    ic1, ic2, ic3 = st.columns(3)
    for col, key in zip((ic1, ic2, ic3), ("water_stress", "heat_stress", "environmental")):
        sub = risk.get(key) or {}
        lvl = (sub.get("level") or "unknown").lower()
        col.markdown(
            f"""<div class="indicator"><div class="ind-label">{t(_INDICATOR_KEYS[key], lang)}</div>
                {_badge(lvl)}</div>""",
            unsafe_allow_html=True,
        )

    # --- 3. Why? ------------------------------------------------------------- #
    reasons = _why_reasons(risk)
    if reasons:
        st.markdown(f"#### {t('why_header', lang)}")
        for r in reasons:
            st.markdown(f"- {r}")

    # --- 4. Recommended actions ----------------------------------------------- #
    actions = rec.get("recommended_actions", [])
    if actions:
        st.markdown(f"#### {t('actions_header', lang)}")
        for i, a in enumerate(actions[:3], start=1):
            st.markdown(f"{i}. {a}")

    # --- 5. Evidence indicator ------------------------------------------------- #
    evidence = rec.get("evidence") or []
    evidence_source = rec.get("evidence_source", "")
    if evidence:
        n = len(evidence)
        st.markdown(
            f"**{t('evidence_checked', lang)}** &nbsp;·&nbsp; {t('sources_used_tmpl', lang, n=n)} "
            f"&nbsp;·&nbsp; {t('evidence_live', lang) if evidence_source == 'exa' else t('evidence_sample', lang)}"
        )
    elif combined_level == "low":
        st.caption(t("evidence_not_needed", lang))

    # --- 6. action row: View Evidence / View Details --------------------------- #
    bcol1, bcol2, _ = st.columns([1, 1, 2])
    if evidence and bcol1.button(t("view_evidence_btn", lang), width="stretch"):
        st.session_state["show_evidence"] = not st.session_state["show_evidence"]
    if bcol2.button(t("view_details_btn", lang), width="stretch"):
        st.session_state["show_details"] = not st.session_state["show_details"]

    if evidence and st.session_state["show_evidence"]:
        with st.container(border=True):
            for ev in evidence:
                title = ev.get("title", "source")
                url = ev.get("url", "")
                domain = _evidence_domain(url) if url else ""
                head = f"[{title}]({url})" if url else title
                badge = "`LIVE`" if evidence_source == "exa" else "`SAMPLE`"
                st.markdown(f"{badge} **{head}** &nbsp;<span class='small'>{domain}</span>", unsafe_allow_html=True)
                if ev.get("snippet"):
                    st.markdown(f'<span class="small">{ev["snippet"]}</span>', unsafe_allow_html=True)
                st.markdown("---")

    # --- 7. minimized agent activity checklist ---------------------------------- #
    st.markdown(f"#### {t('agent_activity', lang)}")
    tools_used = set(result.tools_used)
    items = [
        (t("chk_risk", lang), "calculate_risk" in tools_used),
        (t("chk_evidence_done", lang) if "search_web" in tools_used else t("chk_evidence_skip", lang),
         "search_web" in tools_used),
        (t("chk_reco", lang), "generate_recommendation" in tools_used),
    ]
    checklist_html = "<div class='checklist'>" + "".join(
        f"<div class='{'ok' if done else 'skip'}'>{'✓' if done else '·'} {label}</div>"
        for label, done in items
    ) + "</div>"
    st.markdown(checklist_html, unsafe_allow_html=True)

    # --- 8. Technical Details (progressive disclosure) --------------------------- #
    if st.session_state["show_details"]:
        with st.container(border=True):
            st.markdown(f"### {t('technical_details_header', lang)}")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Reasoning mode", result.reasoning_mode)
            m2.metric("Tools used", len(result.tools_used))
            m3.metric("Execution", f"{result.execution_ms:.0f} ms")
            m4.metric("Confidence", f"{float(rec.get('confidence', risk.get('confidence', 0)) or 0):.0%}")

            for note in obs.notes:
                st.markdown(f'<span class="small">• {note}</span>', unsafe_allow_html=True)

            tab_obs, tab_env, tab_risk, tab_rec, tab_conf, tab_run = st.tabs([
                t("tab_visual", lang), t("tab_env", lang), t("tab_risk", lang),
                t("tab_rec", lang), t("tab_conf", lang), t("tab_run", lang),
            ])

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
                               "**combined risk** above weights this together with image and weather.")
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
                    if evidence:
                        st.caption("See the Evidence section above for cited sources.")
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
        st.markdown(f"### {t('agent_activity', lang)}")
        st.info(t("empty_state", lang))

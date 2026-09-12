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
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agent.agent import SahelAgent  # noqa: E402
from app.agent.assistant import (  # noqa: E402
    GENERAL_SUGGESTED_QUESTIONS,
    SUGGESTED_QUESTIONS,
    answer as assistant_answer,
    needs_live_evidence,
)
from app.agent.autonomy import compute_autonomy  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.i18n import LANGUAGES, PARTIAL_NOTICE, t  # noqa: E402
from app.core.schemas import AgentInput, GrowthStage, Location, SensorReadings  # noqa: E402
from app.core.security import validate_image_upload  # noqa: E402
from app.data.demo_data import get_scenario, list_scenarios, load_scenario_image  # noqa: E402
from app.tools.registry import get_registry  # noqa: E402

st.set_page_config(page_title="SAHEL Agent", page_icon="🌍", layout="wide")


def _css(theme: str) -> str:
    """Force a consistent light/dark look regardless of the browser's own
    Streamlit theme setting — driven by the toggle button, not guessed.

    Design language: one accent (emerald), one neutral ramp, a restrained
    spacing/radius/shadow scale — simple on the surface, precise underneath.
    Pure styling: no component here changes what data is shown, only how.
    """
    if theme == "dark":
        bg, bg2, card, text, sub, faint, border = (
            "#0b0f14", "#121821", "#151c26", "#eef1f5", "#9aa5b1", "#6b7684", "#232b36"
        )
        accent, accent_soft, accent_text = "#34d399", "#0f2a22", "#6ee7b7"
        shadow = "0 1px 2px rgba(0,0,0,.4), 0 8px 24px -8px rgba(0,0,0,.5)"
    else:
        bg, bg2, card, text, sub, faint, border = (
            "#ffffff", "#f7f8fa", "#ffffff", "#0f172a", "#586174", "#8a93a3", "#e8eaee"
        )
        accent, accent_soft, accent_text = "#059669", "#ecfdf5", "#047857"
        shadow = "0 1px 2px rgba(15,23,42,.04), 0 8px 24px -12px rgba(15,23,42,.12)"
    return f"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
    :root {{
        --bg: {bg}; --bg2: {bg2}; --card: {card}; --text: {text}; --sub: {sub}; --faint: {faint};
        --border: {border}; --accent: {accent}; --accent-soft: {accent_soft}; --accent-text: {accent_text};
        --shadow: {shadow}; --radius: 14px; --radius-sm: 9px;
        --background-color: {bg}; --secondary-background-color: {bg2}; --text-color: {text};
    }}
    html, body, .stApp {{
        background-color: var(--bg) !important; color: var(--text) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }}
    [data-testid="stSidebar"] {{ background-color: var(--bg2) !important; border-right: 1px solid var(--border); }}
    [data-testid="stSidebar"] * {{ font-family: 'Inter', sans-serif !important; }}
    [data-testid="stHeader"] {{ background-color: transparent !important; }}
    .stApp, .stApp p, .stApp label, .stApp span, .stApp li {{ color: var(--text); }}
    .block-container {{ padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1080px; }}

    h1, h2, h3, h4 {{ letter-spacing: -0.02em; font-weight: 700; }}
    h3 {{ font-size: 1.05rem; font-weight: 700; margin-bottom: 0.5rem; }}
    h4 {{ font-size: 0.95rem; font-weight: 700; }}

    /* buttons: one confident primary, quiet secondaries */
    .stButton > button {{
        border-radius: var(--radius-sm) !important; font-weight: 600 !important;
        border: 1px solid var(--border) !important; transition: transform .05s ease, box-shadow .15s ease;
    }}
    .stButton > button:hover {{ border-color: var(--accent) !important; }}
    .stButton > button[kind="primary"] {{
        background: var(--accent) !important; border-color: var(--accent) !important;
        color: #ffffff !important; box-shadow: var(--shadow); padding: 0.65rem 1rem !important;
        font-size: 0.98rem !important;
    }}
    .stButton > button[kind="primary"]:hover {{ filter: brightness(1.06); transform: translateY(-1px); }}
    .stButton > button[kind="secondary"] {{ background: var(--card) !important; color: var(--text) !important; }}

    /* top bar */
    .sahel-brand {{ display:flex; align-items:center; gap:10px; height: 42px; }}
    .sahel-brand .mark {{
        width:32px; height:32px; border-radius:9px; background: var(--accent);
        display:flex; align-items:center; justify-content:center; font-size:16px; flex-shrink:0;
        box-shadow: var(--shadow);
    }}
    .sahel-brand .word {{ font-weight:800; font-size:1.15rem; letter-spacing:-0.02em; color: var(--text); }}
    .sahel-sub {{ color: var(--sub) !important; font-size: 1rem; margin-top: 2px; margin-bottom: 0; font-weight: 450; }}

    /* generic surfaces */
    .sahel-card {{
        background: var(--card); border:1px solid var(--border); border-radius: var(--radius);
        padding: 20px 22px; box-shadow: var(--shadow);
    }}
    .small {{ color: var(--sub) !important; font-size:0.82rem; }}
    .faint {{ color: var(--faint) !important; font-size: 0.78rem; }}
    hr {{ border-color: var(--border) !important; margin: 1.1rem 0 !important; }}
    [data-testid="stExpander"] {{ border:1px solid var(--border) !important; border-radius: var(--radius-sm) !important;
                                   background: var(--card); }}
    [data-testid="stFileUploaderDropzone"] {{ border-radius: var(--radius-sm) !important;
                                               background: var(--bg2) !important; border-color: var(--border) !important; }}

    /* form controls: match the theme instead of Streamlit's fixed light chrome */
    input, textarea, select,
    [data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div,
    [data-baseweb="base-input"] {{
        background-color: var(--bg2) !important; color: var(--text) !important;
        border-color: var(--border) !important;
    }}
    [data-baseweb="select"] svg {{ fill: var(--sub) !important; }}
    ::placeholder {{ color: var(--faint) !important; opacity: 1 !important; }}
    [data-testid="stFileUploader"] section {{ background: transparent !important; }}
    [data-testid="stFileUploaderDropzone"] button {{ background: var(--card) !important; color: var(--text) !important; }}

    /* badges */
    .badge {{ display:inline-flex; align-items:center; gap:5px; padding: 3px 11px; border-radius: 999px;
              font-size: 0.72rem; font-weight: 700; letter-spacing: 0.01em; margin-right: 6px; }}
    .badge-low {{ background:#dcfce7; color:#166534; }}
    .badge-moderate, .badge-medium {{ background:#fef3c7; color:#92400e; }}
    .badge-high {{ background:#fee2e2; color:#991b1b; }}
    .badge-unknown {{ background: var(--border); color: var(--sub); }}

    /* section eyebrow (small caps label above a section) */
    .eyebrow {{ font-size:0.7rem; letter-spacing:0.09em; color: var(--sub); font-weight:700;
                text-transform: uppercase; margin-bottom:8px; }}

    /* risk hero: the one thing a judge must see in 3 seconds */
    .risk-hero {{
        background: linear-gradient(180deg, var(--card) 0%, var(--bg2) 100%);
        border:1px solid var(--border); border-radius: var(--radius);
        padding:24px 26px; margin: 12px 0 18px; box-shadow: var(--shadow); position: relative; overflow:hidden;
    }}
    .risk-hero::before {{
        content:""; position:absolute; left:0; top:0; bottom:0; width:5px;
    }}
    .risk-hero.low::before {{ background:#16a34a; }}
    .risk-hero.moderate::before, .risk-hero.medium::before {{ background:#d97706; }}
    .risk-hero.high::before {{ background:#dc2626; }}
    .risk-hero.unknown::before {{ background: var(--border); }}
    .risk-eyebrow {{ font-size:0.72rem; letter-spacing:0.09em; color: var(--sub); font-weight:700;
                      margin-bottom:10px; text-transform: uppercase; }}
    .risk-badge-big {{ font-size:2.1rem; font-weight:800; letter-spacing:-0.02em; display:inline-block; margin-right:14px; }}
    .risk-badge-big.low {{ color:#16a34a; }}
    .risk-badge-big.moderate, .risk-badge-big.medium {{ color:#d97706; }}
    .risk-badge-big.high {{ color:#dc2626; }}
    .risk-badge-big.unknown {{ color: var(--sub); }}
    .risk-situation {{ color: var(--text); font-size:1rem; margin-top:8px; }}
    .risk-driver {{ font-size:1rem; font-weight:600; margin-top:12px; color: var(--text); }}

    /* three-up indicators */
    .indicator {{ border:1px solid var(--border); background: var(--card); border-radius: var(--radius-sm);
                  padding:14px 16px; text-align:left; box-shadow: var(--shadow); }}
    .indicator .ind-label {{ font-size:0.76rem; color: var(--sub); margin-bottom:7px; font-weight:600; }}

    /* step checklist: reads like a receipt of real work done */
    .steps {{ display:flex; flex-direction:column; gap:2px; }}
    .step {{ display:flex; align-items:flex-start; gap:10px; padding:7px 0; font-size:0.88rem; }}
    .step .dot {{ width:18px; height:18px; border-radius:50%; flex-shrink:0; display:flex; align-items:center;
                  justify-content:center; font-size:11px; margin-top:1px; }}
    .step.ok .dot {{ background: var(--accent-soft); color: var(--accent-text); }}
    .step.skip .dot {{ background: var(--border); color: var(--sub); }}
    .step.ok span.label {{ color: var(--text); font-weight: 500; }}
    .step.skip span.label {{ color: var(--sub); }}

    /* technical details: same rigor, framed as "inside the agent" */
    .tech-panel {{ border:1px solid var(--border); border-radius: var(--radius); background: var(--card);
                   padding: 22px 24px; box-shadow: var(--shadow); margin-top: 6px; }}
    .tech-kicker {{ font-size:0.78rem; color: var(--sub); margin-bottom: 4px; }}
    [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid var(--border) !important; }}
    [data-baseweb="tab"] {{ font-weight: 600 !important; font-size: 0.86rem !important; }}

    /* native bordered containers -> match the card language */
    [data-testid="stVerticalBlockBorderWrapper"] > div,
    div[data-testid="stContainer"] {{ border-radius: var(--radius) !important; }}
    [data-testid="stVerticalBlockBorderWrapper"] {{ box-shadow: var(--shadow); border-radius: var(--radius) !important; }}
    pre, code {{ font-family: 'JetBrains Mono', ui-monospace, Menlo, monospace !important; }}
    .stCodeBlock {{ border-radius: var(--radius-sm) !important; }}

    /* mini-stats: like st.metric but never truncates a long value */
    .mini-stat-row {{ display:flex; gap:28px; flex-wrap:wrap; margin: 8px 0 6px; }}
    .mini-stat {{ min-width: 100px; }}
    .mini-stat .msv-label {{ font-size:0.72rem; color: var(--sub); font-weight:700; margin-bottom:4px;
                              text-transform:uppercase; letter-spacing:0.04em; }}
    .mini-stat .msv-value {{ font-size:1.2rem; font-weight:700; color: var(--text); line-height:1.3; }}

    /* evidence cards */
    .ev-card {{ border:1px solid var(--border); border-radius: var(--radius-sm); padding:12px 14px;
                margin-bottom:8px; background: var(--card); }}
    .ev-tag {{ font-size:0.65rem; font-weight:800; letter-spacing:0.04em; padding:2px 7px; border-radius:5px;
               background: var(--accent-soft); color: var(--accent-text); margin-right:8px; }}

    /* empty state */
    .empty-state {{ border:1.5px dashed var(--border); border-radius: var(--radius); padding: 40px 28px;
                     text-align:center; color: var(--sub); background: var(--bg2); }}
    .empty-state .glyph {{ font-size: 2rem; margin-bottom: 10px; }}
    .empty-state .headline {{ color: var(--text); font-weight: 700; font-size: 1rem; margin-bottom: 4px; }}

    /* Ask the Agent dialog: st.dialog renders in a portal outside .stApp,
       so it needs its own theme pass rather than inheriting the cascade. */
    [role="dialog"] {{ background: var(--bg) !important; border: 1px solid var(--border) !important; }}
    [role="dialog"] * {{ color: var(--text); }}
    [role="dialog"] input {{ background: var(--bg2) !important; color: var(--text) !important; }}

    /* chat */
    .chat-bubble-user {{ background: var(--accent-soft); border:1px solid transparent; color: var(--accent-text);
                          border-radius: 12px 12px 3px 12px; padding:9px 13px; margin:4px 0 4px auto;
                          font-size:0.9rem; max-width: 92%; width: fit-content; }}
    .chat-bubble-agent {{ background: var(--bg2); border:1px solid var(--border); color: var(--text);
                           border-radius: 12px 12px 12px 3px; padding:9px 13px; margin:4px auto 2px 0;
                           font-size:0.9rem; max-width: 92%; width: fit-content; }}
    </style>
    """


st.session_state.setdefault("theme", "light")
st.html(_css(st.session_state["theme"]))

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
lang = st.session_state["lang"]

# --- Top bar: brand on the left, everything else (theme / language / chat) --
# --- quiet utility icons on the right — none of it competes with ANALYZE. ---
_bar_l, _bar_theme, _bar_lang, _bar_chat = st.columns([4.2, 1, 1, 1.6])
with _bar_l:
    st.markdown(
        f'<div class="sahel-brand"><div class="mark">🌍</div>'
        f'<div class="word">{t("app_title", lang)}</div></div>',
        unsafe_allow_html=True,
    )
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
st.markdown(f'<p class="sahel-sub">{t("app_tagline", lang)}</p>', unsafe_allow_html=True)
if lang == "bm":
    st.caption(f"ℹ️ {PARTIAL_NOTICE}")


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


def _llm_status_line() -> str:
    """One honest sentence about the reasoning path actually in effect — never
    a raw stack trace, never a secret. Shown only in Technical Details."""
    if settings.offline_first:
        return "Local mode — offline/demo, no external LLM is called."
    if settings.llm_provider == "mock":
        return "Local mode — mock reasoning (no real LLM provider configured)."
    from app.llm.factory import get_llm_client

    client = get_llm_client(settings.llm_provider)
    health = client.health_check()
    label = client.name.capitalize()
    if health.state.value == "READY":
        return f"{label} connected."
    return f"{label} unavailable ({health.detail}) — local fallback active."


def _evidence_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "") or url
    except Exception:  # noqa: BLE001
        return url


def _bold(text: str) -> str:
    """`**x**` -> `<strong>x</strong>` — for translated strings embedded inside
    a raw HTML block, where markdown's own ** syntax doesn't apply."""
    import re

    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def _mini_stats(pairs: list[tuple[str, str]]) -> None:
    """Like a row of st.metric, but wraps instead of truncating long values
    (e.g. a full autonomy level sentence) — same data, just legible."""
    cells = "".join(
        f'<div class="mini-stat"><div class="msv-label">{label}</div>'
        f'<div class="msv-value">{value}</div></div>'
        for label, value in pairs
    )
    st.markdown(f'<div class="mini-stat-row">{cells}</div>', unsafe_allow_html=True)


@st.dialog(t("chat_title", lang))
def _ask_agent_dialog(result, agent_input):
    st.caption(t("chat_subtitle", lang))
    if result is not None:
        st.caption(f"🟢 {t('chat_context_available', lang)}")

    history = st.session_state["chat_history"]
    if not history:
        st.markdown(t("chat_welcome_pre", lang))

    for entry in history:
        role, text_, meta = entry if len(entry) == 3 else (*entry, None)
        cls = "chat-bubble-user" if role == "user" else "chat-bubble-agent"
        st.markdown(f'<div class="{cls}">{text_}</div>', unsafe_allow_html=True)
        if role == "agent" and meta:
            if meta.get("source") == "llm":
                st.caption(f"🤖 {t('chat_answered_by_llm', lang, provider=meta.get('provider', '').capitalize())}")
            elif meta.get("source") == "router":
                st.caption(f"⚙️ {t('chat_answered_by_router', lang)}")

    # Canonical (English) question paired with its translated display label —
    # the router matches English keywords, but nothing shown to the user has
    # to be in English just because of that.
    if result is not None:
        pairs = list(zip(SUGGESTED_QUESTIONS, ("sugg_why", "sugg_first", "sugg_evidence")))
    else:
        pairs = list(zip(GENERAL_SUGGESTED_QUESTIONS, ("sugg_analyze", "sugg_how", "sugg_confidence")))
    sug_cols = st.columns(len(pairs))
    for i, (canonical_q, label_key) in enumerate(pairs):
        if sug_cols[i].button(t(label_key, lang), key=f"_sugg_{i}", width="stretch"):
            _ask(canonical_q, result, agent_input, display_as=t(label_key, lang))
            st.rerun()

    if lang != "en" and t("chat_lang_note", lang):
        st.caption(f"ℹ️ {t('chat_lang_note', lang)}")

    q_col, send_col = st.columns([5, 1])
    # Keyed on history length so the field clears after each send instead of
    # re-showing the previous question (a fixed key would retain stale text).
    input_key = f"_chat_input_{len(history)}"
    q_text = q_col.text_input(t("chat_placeholder", lang), key=input_key, label_visibility="collapsed",
                               placeholder=t("chat_placeholder", lang))
    if send_col.button(t("chat_send", lang), width="stretch") and q_text.strip():
        _ask(q_text.strip(), result, agent_input)
        st.rerun()

    if st.button(t("chat_voice", lang), key="_chat_voice"):
        st.caption(t("chat_voice_note", lang))


def _ask(question: str, result, agent_input, display_as: str | None = None) -> None:
    st.session_state["chat_history"].append(("user", display_as or question, None))
    thinking = t("chat_checking_evidence", lang) if needs_live_evidence(question, result) else t("chat_thinking", lang)
    with st.spinner(thinking):
        resp = assistant_answer(question, result, agent_input, lang=lang)
    meta = {"source": resp.get("source"), "provider": resp.get("provider")}
    st.session_state["chat_history"].append(("agent", resp["text"], meta))


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
        st.caption(f"🔌 {_llm_status_line()}")
        st.caption(t("offline_caption", lang))


loaded = st.session_state.get("loaded", {})
ls = loaded.get("sensors", {}) if loaded else {}
ll = loaded.get("location", {}) if loaded else {}

# --------------------------------------------------------------------------- #
# Input
# --------------------------------------------------------------------------- #
if settings.demo_judge_mode:
    st.info(t("judge_mode_banner", lang, scenario=loaded.get("title", settings.demo_judge_scenario)))

_existing_result = st.session_state.get("result")
with _chat_slot:
    if st.button(t("chat_button", lang), width="stretch", key="_open_chat"):
        _ask_agent_dialog(_existing_result, st.session_state.get("last_agent_input"))

st.write("")

left, right = st.columns([1, 1])
with left:
    st.markdown(f'<div class="eyebrow">{t("input_header", lang)}</div>', unsafe_allow_html=True)
    form_card = st.container(border=True)
    with form_card:
        st.markdown(f"**🖼️ {t('image_uploader', lang)}**")
        up = st.file_uploader(t("image_uploader", lang), type=["jpg", "jpeg", "png", "webp"],
                               label_visibility="collapsed")
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

        st.markdown(f"**📡 {t('sensor_readings_header', lang)}**")
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

        st.markdown(f"**📍 {t('location_header', lang)}**")
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

    st.write("")
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
        st.markdown(f'<div class="eyebrow">{t("agent_activity", lang)}</div>', unsafe_allow_html=True)
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
        f"""<div class="risk-hero {combined_level}">
            <div class="risk-eyebrow">{t('risk_hero_label', lang)}</div>
            <span class="risk-badge-big {combined_level}">{t(f'badge_{combined_level}', lang) if f'badge_{combined_level}' in _BADGE_KEYS else combined_level.upper()}</span>
            <div class="risk-situation">{result.situation_line()}</div>
            <div class="risk-driver">{driver_line}</div>
        </div>""",
        unsafe_allow_html=True,
    )

    # --- 2. three compact indicators ---------------------------------------- #
    _IND_ICON = {"water_stress": "💧", "heat_stress": "🌡️", "environmental": "🌱"}
    ic1, ic2, ic3 = st.columns(3)
    for col, key in zip((ic1, ic2, ic3), ("water_stress", "heat_stress", "environmental")):
        sub = risk.get(key) or {}
        lvl = (sub.get("level") or "unknown").lower()
        col.markdown(
            f"""<div class="indicator"><div class="ind-label">{_IND_ICON[key]} {t(_INDICATOR_KEYS[key], lang)}</div>
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
        for ev in evidence:
            title = ev.get("title", "source")
            url = ev.get("url", "")
            domain = _evidence_domain(url) if url else ""
            head = f"[{title}]({url})" if url else title
            tag = t("evidence_live", lang) if evidence_source == "exa" else t("evidence_sample", lang)
            snippet = f'<div class="small" style="margin-top:4px;">{ev["snippet"]}</div>' if ev.get("snippet") else ""
            st.markdown(
                f"""<div class="ev-card"><span class="ev-tag">{tag.split(' ', 1)[-1].upper() if tag else 'SOURCE'}</span>
                    <strong>{head}</strong> <span class="small">{domain}</span>{snippet}</div>""",
                unsafe_allow_html=True,
            )

    # --- 7. minimized agent activity checklist ---------------------------------- #
    st.markdown(f'<div class="eyebrow" style="margin-top:18px;">{t("agent_activity", lang)}</div>', unsafe_allow_html=True)
    tools_used = set(result.tools_used)
    items = [
        (t("chk_risk", lang), "calculate_risk" in tools_used),
        (t("chk_evidence_done", lang) if "search_web" in tools_used else t("chk_evidence_skip", lang),
         "search_web" in tools_used),
        (t("chk_reco", lang), "generate_recommendation" in tools_used),
    ]
    steps_html = "<div class='steps'>" + "".join(
        f"<div class='step {'ok' if done else 'skip'}'><div class='dot'>{'✓' if done else '·'}</div>"
        f"<span class='label'>{label}</span></div>"
        for label, done in items
    ) + "</div>"
    st.markdown(steps_html, unsafe_allow_html=True)

    # --- 8. Technical Details (progressive disclosure) --------------------------- #
    if st.session_state["show_details"]:
        with st.container(border=True):
            st.markdown(f"### 🔬 {t('technical_details_header', lang)}")
            st.markdown(
                f'<div class="tech-kicker">{_t_or("technical_details_sub", "Everything the agent actually did.")}</div>',
                unsafe_allow_html=True,
            )
            _mini_stats([
                ("Reasoning mode", result.reasoning_mode),
                ("Tools used", str(len(result.tools_used))),
                ("Execution", f"{result.execution_ms:.0f} ms"),
                ("Confidence", f"{float(rec.get('confidence', risk.get('confidence', 0)) or 0):.0%}"),
            ])

            for note in obs.notes:
                st.markdown(f'<span class="small">• {note}</span>', unsafe_allow_html=True)

            tab_auto, tab_obs, tab_env, tab_risk, tab_rec, tab_conf, tab_run = st.tabs([
                t("tab_autonomy", lang), t("tab_visual", lang), t("tab_env", lang), t("tab_risk", lang),
                t("tab_rec", lang), t("tab_conf", lang), t("tab_run", lang),
            ])

            with tab_auto:
                auto = compute_autonomy(result, get_registry())
                st.caption(t("autonomy_intro", lang))
                _mini_stats([
                    (t("autonomy_mode", lang), auto["operating_mode"]),
                    (t("autonomy_level", lang), auto["level_label"]),
                ])
                st.progress(min(auto["level"], 3) / 3)

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**{t('autonomy_active', lang)}**")
                    for cap in auto["active_capabilities"]:
                        st.markdown(f"- ✅ {cap}")
                with c2:
                    st.markdown(f"**{t('autonomy_unavailable', lang)}**")
                    for cap in auto["unavailable_capabilities"]:
                        st.markdown(f'<span class="small">- ⛔ {cap}</span>', unsafe_allow_html=True)

                st.markdown(f"**{t('autonomy_why', lang)}**")
                st.markdown(auto["why"])

                st.markdown(f"**{t('autonomy_activity', lang)}**")
                for note in auto["notes"]:
                    st.markdown(f"- {note}")

                st.markdown(f"**{t('autonomy_constraints', lang)}**")
                for c in auto["constraints"]:
                    st.markdown(f'<span class="small">- {c}</span>', unsafe_allow_html=True)

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
        st.markdown(f'<div class="eyebrow">{t("agent_activity", lang)}</div>', unsafe_allow_html=True)
        st.markdown(
            f"""<div class="empty-state">
                <div class="glyph">🛰️</div>
                <div class="headline">{_t_or('empty_state_headline', 'Ready when you are')}</div>
                <div>{_bold(t('empty_state', lang))}</div>
            </div>""",
            unsafe_allow_html=True,
        )

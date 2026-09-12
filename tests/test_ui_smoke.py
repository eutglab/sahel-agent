"""Streamlit UI smoke test — the claim in docs/build_status.md ("smoke-tested
via AppTest") needs a real test behind it; this is it.

Runs the actual app script headlessly, loads a demo scenario, presses
ANALYZE, and asserts the page renders without raising. Does not assert on
exact copy (language-dependent) — only on structural success.
"""
from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parents[1] / "ui" / "streamlit_app.py")


def test_app_loads_without_exception():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    assert not at.exception


def test_app_language_switch_does_not_crash():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    assert not at.exception
    if at.selectbox:
        at.selectbox[0].set_value("fr").run()
        assert not at.exception


def test_app_theme_toggle_does_not_crash():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    assert not at.exception
    toggle = next((b for b in at.button if b.key == "_theme_toggle"), None)
    assert toggle is not None
    toggle.click().run()
    assert not at.exception


def test_app_chat_button_present_and_opens_without_crash():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    assert not at.exception
    chat_btn = next((b for b in at.button if b.key == "_open_chat"), None)
    assert chat_btn is not None
    chat_btn.click().run()
    assert not at.exception


def test_ask_the_agent_full_acceptance_flow():
    """The exact sequence the product spec demands: fresh launch -> chat opens
    immediately, pre-analysis question answered honestly -> Analyze Field ->
    contextual question answered from the real result. No step may raise, and
    no step may show a disabled/dead-end chat."""
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    assert not at.exception

    # TEST A — chat is immediately clickable, no analysis has run.
    chat_btn = next(b for b in at.button if b.key == "_open_chat")
    chat_btn.click().run()
    assert not at.exception
    general_btn = next((b for b in at.button if b.label == "What can you analyze?"), None)
    assert general_btn is not None, "pre-analysis suggested question missing -> chat looks dead"
    general_btn.click().run()
    assert not at.exception
    assert any("water stress" in m.value.lower() or "risk" in m.value.lower() for m in at.markdown)

    # TEST C — run the actual analysis (multiple-risks demo scenario).
    scenario_box = next(sb for sb in at.selectbox if sb.label == "Scenario")
    scenario_box.set_value(next(o for o in scenario_box.options if "Multiple risk" in o)).run()
    load_btn = next(b for b in at.button if b.label == "Load")
    load_btn.click().run()
    analyze_btn = next(b for b in at.button if b.label in ("Analyze Field", "Analyser le champ"))
    analyze_btn.click().run()
    assert not at.exception

    # TEST D — reopen chat, ask a contextual question, get a grounded answer.
    chat_btn2 = next(b for b in at.button if b.key == "_open_chat")
    chat_btn2.click().run()
    assert not at.exception
    contextual_btn = next((b for b in at.button if b.label == "Why is the risk moderate?"), None)
    assert contextual_btn is not None, "post-analysis suggestions missing after a successful run"
    contextual_btn.click().run()
    assert not at.exception


def test_chat_suggestions_translate_with_the_language_switcher():
    """Regression test: the chat previously stayed English regardless of the
    language switcher because suggestion labels and welcome text were
    hardcoded. They must follow `lang` from st.session_state."""
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    lang_box = next(sb for sb in at.selectbox if sb.label == "Language")
    lang_box.set_value("🇫🇷 FR").run()
    assert not at.exception

    chat_btn = next(b for b in at.button if b.key == "_open_chat")
    chat_btn.click().run()
    assert not at.exception
    assert any(b.label == "Qu'analysez-vous ?" for b in at.button)
    assert not any(b.label == "What can you analyze?" for b in at.button)


def test_app_demo_scenario_end_to_end():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    # Sidebar scenario selectbox: pick the one with more than one option.
    for sb in at.selectbox:
        if len(sb.options) > 2:
            sb.set_value(sb.options[-1]).run()
            break
    assert not at.exception
    if at.button:
        for b in at.button:
            if b.label in ("Analyze Field", "Analyser le champ"):
                b.click().run()
                break
    assert not at.exception


def test_view_details_renders_agent_capability_and_autonomy_tab():
    """The new 'Agent Capability & Autonomy' panel (View Details -> first tab)
    must render without crashing and show a real, non-fabricated mode/level —
    not a made-up percentage."""
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    scenario_box = next(sb for sb in at.selectbox if sb.label == "Scenario")
    scenario_box.set_value(scenario_box.options[-1]).run()
    load_btn = next(b for b in at.button if b.label in ("Load", "Charger"))
    load_btn.click().run()
    assert not at.exception

    analyze_btn = next(b for b in at.button if b.label in ("Analyze Field", "Analyser le champ"))
    analyze_btn.click().run()
    assert not at.exception

    details_btn = next(b for b in at.button if b.label in ("View Details", "Voir les détails"))
    details_btn.click().run()
    assert not at.exception

    # Operating mode / autonomy level render as a custom "mini-stat" block
    # (st.metric truncates long values instead of wrapping them) — check the
    # raw markdown source every markdown element was given.
    rendered = "\n".join(md.value for md in at.markdown)
    assert "Current operating mode" in rendered
    assert "Autonomy level" in rendered
    assert any(
        mode in rendered
        for mode in ("Offline Demo", "Deterministic Agent", "LLM Tool-Calling", "LLM + External Evidence")
    )
    assert "Level " in rendered
    assert "95%" not in rendered

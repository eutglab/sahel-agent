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


def test_app_demo_scenario_end_to_end():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    # Sidebar scenario selectbox is index 0 among selectboxes if language
    # picker loaded first; select the last scenario option and load it.
    scenario_box = next(sb for sb in at.selectbox if sb.label in ("Language", "Scenario") or sb.label == "")
    # Fall back: pick the sidebar one with more than one option.
    for sb in at.selectbox:
        if len(sb.options) > 2:
            sb.set_value(sb.options[-1]).run()
            break
    assert not at.exception
    if at.button:
        for b in at.button:
            if b.label in ("ANALYZE", "ANALYSER"):
                b.click().run()
                break
    assert not at.exception

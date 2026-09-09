from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def registry():
    from app.tools.registry import get_registry

    return get_registry(refresh=True)


@pytest.fixture()
def multiple_risks_input():
    """The primary demo scenario, loaded exactly as 'Load Demo Scenario' would."""
    from app.core.schemas import AgentInput, Location, SensorReadings
    from app.data.demo_data import get_scenario, load_scenario_image

    scn = get_scenario("multiple_risks")
    return AgentInput(
        text_context=scn.get("text_context", ""),
        image_bytes=load_scenario_image(scn),
        image_name=scn.get("image"),
        sensors=SensorReadings(**scn.get("sensors", {})),
        location=Location(**scn.get("location", {})),
        scenario_id="multiple_risks",
    )


@pytest.fixture()
def block_network(monkeypatch):
    """Make any outbound socket connection raise — proves offline behaviour."""
    import socket

    class _Blocked(socket.socket):
        def connect(self, *a, **k):  # noqa: ANN001
            raise OSError("network access blocked by test")

        def connect_ex(self, *a, **k):  # noqa: ANN001
            raise OSError("network access blocked by test")

    monkeypatch.setattr(socket, "socket", _Blocked)

    def _guard(*a, **k):  # noqa: ANN001
        raise OSError("network access blocked by test")

    monkeypatch.setattr(socket, "create_connection", _guard)
    return True

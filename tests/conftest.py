from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# The test suite must be deterministic and offline no matter what a developer
# has in their local `.env` (e.g. a real LLM_PROVIDER=openrouter + API key for
# manual testing). `app.core.config._load_dotenv` only fills variables that
# aren't already set in the real environment (`os.environ.setdefault`), so
# pinning the safe demo defaults here — before any `app.*` module is first
# imported by test collection — guarantees they win over the .env file.
os.environ.setdefault("ENVIRONMENT", "demo")
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("LLM_PROVIDER", "mock")


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

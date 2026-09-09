from __future__ import annotations

from app.tools.weather.providers.mock import MockWeatherProvider
from app.tools.weather.schema import WeatherInput
from app.tools.weather.tool import build


def test_mock_weather_is_deterministic():
    p = MockWeatherProvider()
    a = p.run(WeatherInput(label="Fictional Site Alpha"))
    b = p.run(WeatherInput(label="Fictional Site Alpha"))
    assert a == b
    assert a["source"].startswith("demo")


def test_weather_tool_falls_back_to_local_or_mock_offline():
    tool = build()
    rec = tool.execute({"label": "Fictional Site Alpha", "latitude": 14.5, "longitude": -4.2})
    assert rec.success
    # In demo mode open-meteo is skipped; a local/mock provider must answer.
    assert rec.provider_used in {"local", "mock"}
    assert "temperature_c" in rec.output


def test_weather_tool_has_terminal_provider():
    tool = build()
    assert tool.providers()[-1].name == "mock"


def test_weather_unknown_location_still_succeeds():
    tool = build()
    rec = tool.execute({"label": "Nowhere In Particular"})
    assert rec.success  # local misses -> mock answers

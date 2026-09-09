from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel

from app.core.config import settings
from app.core.errors import ProviderTimeout, ProviderUnavailable
from app.core.logging import get_logger
from app.core.schemas import MaturityStatus
from app.tools.base import BaseProvider
from app.tools.weather.schema import WeatherInput, WeatherOutput

logger = get_logger("sahel.weather")

_ENDPOINT = "https://api.open-meteo.com/v1/forecast"


class OpenMeteoWeatherProvider(BaseProvider):
    """Real weather via Open-Meteo — free, no API key required.

    IMPLEMENTED. Skipped automatically in offline/demo mode; on any network
    error it raises ``ProviderUnavailable`` so the fallback chain continues.
    """

    name = "open_meteo"
    status = MaturityStatus.IMPLEMENTED
    requires_credentials = False

    def run(self, payload: BaseModel) -> Dict[str, Any]:
        assert isinstance(payload, WeatherInput)
        if settings.offline_first:
            raise ProviderUnavailable("offline/demo mode — real weather skipped")
        if payload.latitude is None or payload.longitude is None:
            raise ProviderUnavailable("open-meteo needs latitude/longitude")

        try:
            import requests
        except ImportError as exc:  # pragma: no cover
            raise ProviderUnavailable(f"requests not installed: {exc}") from exc

        params = {
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "current": "temperature_2m,relative_humidity_2m,precipitation",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
            "forecast_days": 3,
            "timezone": "auto",
        }
        try:
            resp = requests.get(_ENDPOINT, params=params, timeout=settings.tool_timeout_seconds)
        except requests.Timeout as exc:
            raise ProviderTimeout(f"open-meteo timed out after {settings.tool_timeout_seconds}s") from exc
        except requests.RequestException as exc:
            raise ProviderUnavailable(f"open-meteo request failed: {exc}") from exc

        if resp.status_code != 200:
            raise ProviderUnavailable(f"open-meteo HTTP {resp.status_code}")

        data = resp.json()
        current = data.get("current", {})
        daily = data.get("daily", {})

        forecast = []
        days = daily.get("time", [])
        for i, day in enumerate(days):
            forecast.append(
                {
                    "day": day,
                    "temp_max_c": _at(daily.get("temperature_2m_max"), i),
                    "temp_min_c": _at(daily.get("temperature_2m_min"), i),
                    "rainfall_mm": _at(daily.get("precipitation_sum"), i),
                    "rain_probability": _at(daily.get("precipitation_probability_max"), i),
                }
            )

        return WeatherOutput(
            source="open-meteo",
            temperature_c=current.get("temperature_2m"),
            humidity_pct=current.get("relative_humidity_2m"),
            rainfall_mm=current.get("precipitation"),
            rain_probability=_at(daily.get("precipitation_probability_max"), 0),
            forecast=forecast,
            note="Live data from Open-Meteo (open, keyless API).",
        ).model_dump()


def _at(seq, i):
    if isinstance(seq, list) and i < len(seq):
        return seq[i]
    return None

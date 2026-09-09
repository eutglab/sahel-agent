from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel

from app.core.config import get_secret, settings
from app.core.errors import NotIntegratedError, ProviderUnavailable
from app.core.schemas import HealthState, HealthStatus, MaturityStatus
from app.tools.base import BaseProvider
from app.tools.weather.schema import WeatherInput, WeatherOutput

# ---------------------------------------------------------------------------
# HACKATHON WEATHER PROVIDER — skeleton to fill on the day.
#
# 1. Organisers give you: base URL + API key (+ response shape).
# 2. Put them in .env:  HACKATHON_WEATHER_BASE_URL, HACKATHON_WEATHER_API_KEY
# 3. Map their response to WeatherOutput in `_map_response` below.
# 4. Set WEATHER_PROVIDER=hackathon  (or add `hackathon` to WEATHER_FALLBACK_CHAIN)
# 5. python scripts/test_integrations.py
# ---------------------------------------------------------------------------


class HackathonWeatherProvider(BaseProvider):
    name = "hackathon"
    status = MaturityStatus.INTEGRATION_READY
    requires_credentials = True

    def _configured(self) -> bool:
        return bool(settings.hackathon_weather_base_url and get_secret("HACKATHON_WEATHER_API_KEY"))

    def run(self, payload: BaseModel) -> Dict[str, Any]:
        assert isinstance(payload, WeatherInput)
        if not self._configured():
            raise NotIntegratedError(
                "hackathon weather provider not configured "
                "(set HACKATHON_WEATHER_BASE_URL + HACKATHON_WEATHER_API_KEY)"
            )
        try:
            import requests
        except ImportError as exc:  # pragma: no cover
            raise ProviderUnavailable(f"requests not installed: {exc}") from exc

        # --- EDIT THIS BLOCK on hackathon day to match the provided API. ------
        resp = requests.get(
            settings.hackathon_weather_base_url,
            params={"label": payload.label, "lat": payload.latitude, "lon": payload.longitude},
            headers={"Authorization": f"Bearer {get_secret('HACKATHON_WEATHER_API_KEY')}"},
            timeout=settings.tool_timeout_seconds,
        )
        if resp.status_code != 200:
            raise ProviderUnavailable(f"hackathon weather HTTP {resp.status_code}")
        return self._map_response(resp.json())
        # --------------------------------------------------------------------

    @staticmethod
    def _map_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """Map the organiser's payload -> WeatherOutput. Adjust keys as needed."""
        return WeatherOutput(
            source="hackathon-provider",
            temperature_c=data.get("temperature"),
            humidity_pct=data.get("humidity"),
            rainfall_mm=data.get("rainfall"),
            rain_probability=data.get("rain_probability"),
            forecast=[],
            note="Data from hackathon-provided weather API.",
        ).model_dump()

    def health_check(self) -> HealthStatus:
        if self._configured():
            return HealthStatus(
                component="provider:hackathon",
                state=HealthState.WARNING,
                detail="configured but not verified — run test_integrations.py",
                provider=self.name,
            )
        return HealthStatus(
            component="provider:hackathon",
            state=HealthState.WARNING,
            detail="not configured (INTEGRATION_READY)",
            provider=self.name,
        )

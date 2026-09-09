from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel

from app.core.errors import ProviderUnavailable
from app.core.schemas import MaturityStatus
from app.data.demo_data import local_weather
from app.tools.base import BaseProvider
from app.tools.weather.schema import WeatherInput, WeatherOutput


class LocalDatasetWeatherProvider(BaseProvider):
    """Reads bundled weather records from ``demo_data/weather/index.json``.

    IMPLEMENTED: works fully offline. Useful when the real API is unreachable
    but we still want location-specific values rather than pure synthesis.
    """

    name = "local"
    status = MaturityStatus.IMPLEMENTED

    def run(self, payload: BaseModel) -> Dict[str, Any]:
        assert isinstance(payload, WeatherInput)
        record = local_weather(payload.label)
        if not record:
            raise ProviderUnavailable("no local weather record for this location")
        record = dict(record)
        record.setdefault("source", "local dataset")
        record.setdefault("note", "Bundled offline weather record for a fictional location.")
        return WeatherOutput.model_validate(record).model_dump()

from __future__ import annotations

from typing import Dict, List, Type

from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger
from app.core.schemas import MaturityStatus
from app.tools.base import BaseProvider, BaseTool
from app.tools.weather.providers.hackathon import HackathonWeatherProvider
from app.tools.weather.providers.local import LocalDatasetWeatherProvider
from app.tools.weather.providers.mock import MockWeatherProvider
from app.tools.weather.providers.open_meteo import OpenMeteoWeatherProvider
from app.tools.weather.schema import WeatherInput, WeatherOutput

logger = get_logger("sahel.weather")

_PROVIDERS: Dict[str, type[BaseProvider]] = {
    "open_meteo": OpenMeteoWeatherProvider,
    "local": LocalDatasetWeatherProvider,
    "mock": MockWeatherProvider,
    "hackathon": HackathonWeatherProvider,
}


class WeatherTool(BaseTool):
    name = "get_weather"
    description = (
        "Retrieve current conditions and a short forecast (temperature, humidity, "
        "rainfall, rain probability) for a location. Real provider is Open-Meteo "
        "(free, keyless); falls back to a local dataset then synthetic demo data."
    )
    status = MaturityStatus.IMPLEMENTED

    def input_schema(self) -> Type[BaseModel]:
        return WeatherInput

    def output_schema(self) -> Type[BaseModel]:
        return WeatherOutput


def _resolve_chain() -> List[BaseProvider]:
    names: List[str] = []
    primary = settings.weather_provider
    if primary in _PROVIDERS:
        names.append(primary)
    for name in settings.weather_fallback_chain:
        if name in _PROVIDERS and name not in names:
            names.append(name)
    if "mock" not in names:
        names.append("mock")  # guarantee a terminal provider
    return [_PROVIDERS[n]() for n in names]


def build() -> WeatherTool:
    return WeatherTool(providers=_resolve_chain())

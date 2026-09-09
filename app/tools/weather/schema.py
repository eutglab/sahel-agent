from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class WeatherInput(BaseModel):
    label: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class ForecastDay(BaseModel):
    day: str
    temp_max_c: float | None = None
    temp_min_c: float | None = None
    rainfall_mm: float | None = None
    rain_probability: float | None = None


class WeatherOutput(BaseModel):
    source: str                      # "open-meteo" | "local dataset" | "demo" | ...
    temperature_c: float | None = None
    humidity_pct: float | None = None
    rainfall_mm: float | None = None
    rain_probability: float | None = None
    forecast: List[ForecastDay] = Field(default_factory=list)
    note: str = ""

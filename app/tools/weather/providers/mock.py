from __future__ import annotations

import hashlib
from typing import Any, Dict

from pydantic import BaseModel

from app.core.schemas import MaturityStatus
from app.tools.base import BaseProvider
from app.tools.weather.schema import WeatherInput, WeatherOutput


class MockWeatherProvider(BaseProvider):
    """Deterministic synthetic weather — same input always yields same output.

    MOCKED by design: no network, no keys. Used as the last-resort fallback so
    the demo always has *something* plausible and clearly labelled.
    """

    name = "mock"
    status = MaturityStatus.MOCKED

    def run(self, payload: BaseModel) -> Dict[str, Any]:
        assert isinstance(payload, WeatherInput)
        seed_src = (payload.label or f"{payload.latitude},{payload.longitude}" or "sahel").encode()
        seed = int(hashlib.sha256(seed_src).hexdigest(), 16)

        temp = 26 + (seed % 12)                 # 26..37 °C
        humidity = 25 + (seed // 7 % 40)        # 25..64 %
        rain_prob = seed // 13 % 35             # 0..34 %
        rainfall = round((seed // 17 % 6) * 0.5, 1)

        forecast = []
        for i, day in enumerate(["day+1", "day+2", "day+3"]):
            forecast.append(
                {
                    "day": day,
                    "temp_max_c": temp + (i - 1),
                    "temp_min_c": temp - 8 + i,
                    "rainfall_mm": round(rainfall * (0.5 + 0.3 * i), 1),
                    "rain_probability": max(0, rain_prob - 5 * i),
                }
            )

        return WeatherOutput(
            source="demo (synthetic, deterministic)",
            temperature_c=float(temp),
            humidity_pct=float(humidity),
            rainfall_mm=rainfall,
            rain_probability=float(rain_prob),
            forecast=forecast,
            note="Synthetic weather generated locally for demonstration; not a real observation.",
        ).model_dump()

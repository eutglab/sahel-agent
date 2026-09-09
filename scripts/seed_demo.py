"""Generate synthetic demo assets: images, scenarios, local weather, precomputed.

All data here is FICTIONAL and synthetic. No real locations, no real photos.
Run:  python scripts/seed_demo.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.data.demo_data import IMAGE_DIR, PRECOMPUTED_DIR, SCENARIO_DIR, WEATHER_DIR  # noqa: E402


def _make_leaf_image(path: Path, *, green: int, yellow: int, brown: int, dark: int, seed: int) -> None:
    """Cheap synthetic 'canopy' image: colour blocks + noise. Not a real photo."""
    import numpy as np
    from PIL import Image

    rng = np.random.default_rng(seed)
    h = w = 320
    img = np.zeros((h, w, 3), dtype=np.uint8)

    # base green canopy
    img[..., 0] = 40 + rng.integers(0, 30, (h, w))
    img[..., 1] = 110 + rng.integers(0, 40, (h, w))
    img[..., 2] = 40 + rng.integers(0, 25, (h, w))

    def blob(color, count, size):
        for _ in range(count):
            cy, cx = rng.integers(0, h), rng.integers(0, w)
            r = rng.integers(size // 2, size)
            y0, y1 = max(0, cy - r), min(h, cy + r)
            x0, x1 = max(0, cx - r), min(w, cx + r)
            img[y0:y1, x0:x1] = color

    blob((190, 180, 60), yellow, 46)         # yellow patches
    blob((120, 90, 55), brown, 40)           # brown patches
    blob((25, 25, 20), dark, 30)             # dark/necrotic/shadow
    _ = green  # green is the base; parameter kept for readability

    Image.fromarray(img).save(path, "JPEG", quality=85)


SCENARIOS = [
    {
        "id": "normal",
        "title": "Scenario 1 — Normal conditions",
        "description": "Baseline: readings within prototype ranges. Agent runs all applicable tools.",
        "text_context": "Routine check of a field plot under normal conditions.",
        "image": "normal.jpg",
        "sensors": {
            "temperature_c": 26,
            "soil_moisture_pct": 42,
            "air_humidity_pct": 55,
            "rainfall_mm": 6,
            "growth_stage": "vegetative",
        },
        "location": {"label": "Fictional Site Alpha", "latitude": 14.5, "longitude": -4.2},
        "_img": dict(green=1, yellow=2, brown=1, dark=1, seed=1),
    },
    {
        "id": "water_stress",
        "title": "Scenario 2 — Water stress",
        "description": "Very dry soil, no recent rain. Water-stress sub-score should dominate.",
        "text_context": "Soil looks dry, some leaves drooping in the afternoon.",
        "image": "water_stress.jpg",
        "sensors": {
            "temperature_c": 30,
            "soil_moisture_pct": 12,
            "air_humidity_pct": 30,
            "rainfall_mm": 0,
            "growth_stage": "flowering",
        },
        "location": {"label": "Fictional Site Beta", "latitude": 15.1, "longitude": -3.4},
        "_img": dict(green=1, yellow=10, brown=4, dark=3, seed=2),
    },
    {
        "id": "heat_stress",
        "title": "Scenario 3 — Heat stress",
        "description": "High air temperature at a heat-sensitive stage.",
        "text_context": "Heat wave; checking crop condition at midday.",
        "image": "heat_stress.jpg",
        "sensors": {
            "temperature_c": 41,
            "soil_moisture_pct": 33,
            "air_humidity_pct": 22,
            "rainfall_mm": 1,
            "growth_stage": "flowering",
        },
        "location": {"label": "Fictional Site Gamma", "latitude": 16.0, "longitude": -2.9},
        "_img": dict(green=1, yellow=8, brown=3, dark=2, seed=3),
    },
    {
        "id": "multiple_risks",
        "title": "Scenario 4 — Multiple risk factors (primary demo)",
        "description": "Dry soil + heat + low humidity + visible discolouration. Cross-check should show converging evidence.",
        "text_context": "Photo of a plant with partial yellowing. Hot, dry spell continuing.",
        "image": "multiple_risks.jpg",
        "sensors": {
            "temperature_c": 37,
            "soil_moisture_pct": 18,
            "air_humidity_pct": 31,
            "rainfall_mm": 0,
            "growth_stage": "flowering",
        },
        "location": {"label": "Fictional Site Alpha", "latitude": 14.5, "longitude": -4.2},
        "_img": dict(green=1, yellow=16, brown=8, dark=4, seed=4),
    },
    {
        "id": "incomplete_data",
        "title": "Scenario 5 — Incomplete information",
        "description": "No image, no location, only two sensor values. Agent must skip tools and lower confidence.",
        "text_context": "Only partial sensor data available from the field today.",
        "image": None,
        "sensors": {
            "temperature_c": 36,
            "soil_moisture_pct": 20,
            "air_humidity_pct": None,
            "rainfall_mm": None,
            "growth_stage": "fruiting",
        },
        "location": {"label": None, "latitude": None, "longitude": None},
        "_img": None,
    },
]


WEATHER_INDEX = {
    "default": {
        "source": "local dataset",
        "temperature_c": 33.0,
        "humidity_pct": 35.0,
        "rainfall_mm": 0.0,
        "rain_probability": 10.0,
        "forecast": [
            {"day": "day+1", "temp_max_c": 35, "temp_min_c": 22, "rainfall_mm": 0.0, "rain_probability": 8},
            {"day": "day+2", "temp_max_c": 36, "temp_min_c": 23, "rainfall_mm": 0.0, "rain_probability": 12},
            {"day": "day+3", "temp_max_c": 34, "temp_min_c": 22, "rainfall_mm": 0.5, "rain_probability": 20},
        ],
        "note": "Bundled offline weather record (fictional).",
    },
    "locations": {
        "fictional site alpha": {
            "source": "local dataset",
            "temperature_c": 36.0,
            "humidity_pct": 29.0,
            "rainfall_mm": 0.0,
            "rain_probability": 8.0,
            "forecast": [
                {"day": "day+1", "temp_max_c": 38, "temp_min_c": 24, "rainfall_mm": 0.0, "rain_probability": 5},
                {"day": "day+2", "temp_max_c": 39, "temp_min_c": 25, "rainfall_mm": 0.0, "rain_probability": 6},
                {"day": "day+3", "temp_max_c": 37, "temp_min_c": 24, "rainfall_mm": 0.0, "rain_probability": 10},
            ],
            "note": "Bundled offline weather record for a fictional location.",
        },
        "fictional site beta": {
            "source": "local dataset",
            "temperature_c": 31.0,
            "humidity_pct": 33.0,
            "rainfall_mm": 0.0,
            "rain_probability": 12.0,
            "forecast": [
                {"day": "day+1", "temp_max_c": 33, "temp_min_c": 21, "rainfall_mm": 0.0, "rain_probability": 10},
                {"day": "day+2", "temp_max_c": 34, "temp_min_c": 22, "rainfall_mm": 0.0, "rain_probability": 15},
                {"day": "day+3", "temp_max_c": 32, "temp_min_c": 21, "rainfall_mm": 1.0, "rain_probability": 25},
            ],
            "note": "Bundled offline weather record for a fictional location.",
        },
        "fictional site gamma": {
            "source": "local dataset",
            "temperature_c": 40.0,
            "humidity_pct": 20.0,
            "rainfall_mm": 0.0,
            "rain_probability": 4.0,
            "forecast": [
                {"day": "day+1", "temp_max_c": 42, "temp_min_c": 27, "rainfall_mm": 0.0, "rain_probability": 3},
                {"day": "day+2", "temp_max_c": 43, "temp_min_c": 28, "rainfall_mm": 0.0, "rain_probability": 4},
                {"day": "day+3", "temp_max_c": 41, "temp_min_c": 27, "rainfall_mm": 0.0, "rain_probability": 6},
            ],
            "note": "Bundled offline weather record for a fictional location.",
        },
    },
}


def seed_images() -> None:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    for scn in SCENARIOS:
        if not scn.get("image") or not scn.get("_img"):
            continue
        _make_leaf_image(IMAGE_DIR / scn["image"], **scn["_img"])
    print(f"images -> {IMAGE_DIR}")


def seed_scenarios() -> None:
    SCENARIO_DIR.mkdir(parents=True, exist_ok=True)
    for scn in SCENARIOS:
        payload = {k: v for k, v in scn.items() if not k.startswith("_")}
        (SCENARIO_DIR / f"{scn['id']}.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
    print(f"scenarios -> {SCENARIO_DIR}")


def seed_weather() -> None:
    WEATHER_DIR.mkdir(parents=True, exist_ok=True)
    (WEATHER_DIR / "index.json").write_text(json.dumps(WEATHER_INDEX, indent=2), encoding="utf-8")
    print(f"weather -> {WEATHER_DIR / 'index.json'}")


def seed_precomputed() -> None:
    """Freeze the deterministic agent output per scenario as the Level-3 fallback.

    This guarantees the precomputed result matches real agent behaviour.
    """
    PRECOMPUTED_DIR.mkdir(parents=True, exist_ok=True)
    from app.agent.agent import SahelAgent
    from app.data.demo_data import list_scenarios, load_scenario_image
    from app.core.schemas import AgentInput, Location, SensorReadings

    list_scenarios.cache_clear()
    agent = SahelAgent()
    for scn in list_scenarios():
        img = load_scenario_image(scn)
        ai = AgentInput(
            text_context=scn.get("text_context", ""),
            image_bytes=img,
            image_name=scn.get("image"),
            sensors=SensorReadings(**scn.get("sensors", {})),
            location=Location(**scn.get("location", {})),
            scenario_id=scn["id"],
        )
        result = agent.analyze(ai)
        frozen = {
            "scenario_id": scn["id"],
            "modalities_used": result.modalities_used,
            "tools_used": result.tools_used,
            "observation": result.observation.model_dump(),
            "recommendation": result.recommendation,
        }
        (PRECOMPUTED_DIR / f"{scn['id']}.json").write_text(
            json.dumps(frozen, indent=2, default=str), encoding="utf-8"
        )
    print(f"precomputed -> {PRECOMPUTED_DIR}")


if __name__ == "__main__":
    seed_images()
    seed_scenarios()
    seed_weather()
    seed_precomputed()
    print("\nDemo assets ready.")

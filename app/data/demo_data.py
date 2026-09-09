"""Loaders for demo scenarios, local weather data, and precomputed results."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import PROJECT_ROOT

_SAFE_ID = re.compile(r"[^A-Za-z0-9_-]")

DEMO_DIR = PROJECT_ROOT / "demo_data"
SCENARIO_DIR = DEMO_DIR / "scenarios"
IMAGE_DIR = DEMO_DIR / "images"
WEATHER_DIR = DEMO_DIR / "weather"
PRECOMPUTED_DIR = DEMO_DIR / "precomputed"


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def list_scenarios() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not SCENARIO_DIR.exists():
        return out
    for path in sorted(SCENARIO_DIR.glob("*.json")):
        data = _read_json(path)
        data.setdefault("id", path.stem)
        out.append(data)
    return out


def get_scenario(scenario_id: str) -> Optional[Dict[str, Any]]:
    for scn in list_scenarios():
        if scn["id"] == scenario_id:
            return scn
    return None


def load_scenario_image(scenario: Dict[str, Any]) -> Optional[bytes]:
    name = scenario.get("image")
    if not name:
        return None
    path = IMAGE_DIR / name
    if not path.exists():
        return None
    return path.read_bytes()


def local_weather(label: Optional[str]) -> Optional[Dict[str, Any]]:
    """Return a bundled weather record for a named fictional location."""
    index_path = WEATHER_DIR / "index.json"
    if not index_path.exists():
        return None
    index = _read_json(index_path)
    key = (label or "").strip().lower()
    records = index.get("locations", {})
    if key in records:
        return records[key]
    return index.get("default")


def precomputed_result(scenario_id: str) -> Optional[Dict[str, Any]]:
    # Harden against path traversal: the id is only ever a bare slug.
    safe_id = _SAFE_ID.sub("", scenario_id or "")
    if not safe_id:
        return None
    path = PRECOMPUTED_DIR / f"{safe_id}.json"
    if not path.exists() or path.parent != PRECOMPUTED_DIR:
        return None
    return _read_json(path)

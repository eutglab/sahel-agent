"""Centralised configuration and secret access.

- Loads ``.env`` (if present) without any third-party dependency.
- Exposes a single ``settings`` object and ``get_secret(name)``.
- Never prints or logs secret values.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Secrets that must never appear in logs / tracebacks / UI.
_SECRET_KEYS = {
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "HACKATHON_LLM_API_KEY",
    "HACKATHON_WEATHER_API_KEY",
    "WEB_SEARCH_API_KEY",
}


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader: KEY=VALUE lines, ``#`` comments, no interpolation."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Existing real environment variables win over the file.
        os.environ.setdefault(key, value)


_load_dotenv(PROJECT_ROOT / ".env")


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _get_bool(name: str, default: bool) -> bool:
    val = _get(name, str(default)).lower()
    return val in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    try:
        return int(_get(name, str(default)))
    except ValueError:
        return default


def _get_list(name: str, default: str) -> List[str]:
    return [item.strip() for item in _get(name, default).split(",") if item.strip()]


def get_secret(name: str) -> str:
    """Return a secret value from the environment, or ``""`` if unset."""
    return os.environ.get(name, "").strip()


def has_secret(name: str) -> bool:
    return bool(get_secret(name))


def redact(value: str) -> str:
    """Return a safe placeholder for a possibly-secret string."""
    if not value:
        return "<unset>"
    return f"<set:{len(value)} chars>"


@dataclass(frozen=True)
class Settings:
    environment: str = field(default_factory=lambda: _get("ENVIRONMENT", "demo").lower())
    demo_mode: bool = field(default_factory=lambda: _get_bool("DEMO_MODE", True))
    # One-click judge demo: preloads the strongest scenario in the UI.
    demo_judge_mode: bool = field(default_factory=lambda: _get_bool("DEMO_JUDGE_MODE", False))
    demo_judge_scenario: str = field(default_factory=lambda: _get("DEMO_JUDGE_SCENARIO", "multiple_risks"))

    llm_provider: str = field(default_factory=lambda: _get("LLM_PROVIDER", "mock").lower())
    anthropic_model: str = field(default_factory=lambda: _get("ANTHROPIC_MODEL", "claude-haiku-4-5"))
    openai_model: str = field(default_factory=lambda: _get("OPENAI_MODEL", "gpt-4o-mini"))
    hackathon_llm_base_url: str = field(default_factory=lambda: _get("HACKATHON_LLM_BASE_URL"))
    hackathon_llm_model: str = field(default_factory=lambda: _get("HACKATHON_LLM_MODEL"))

    weather_provider: str = field(default_factory=lambda: _get("WEATHER_PROVIDER", "local").lower())
    weather_fallback_chain: List[str] = field(
        default_factory=lambda: _get_list("WEATHER_FALLBACK_CHAIN", "open_meteo,local,mock")
    )
    hackathon_weather_base_url: str = field(default_factory=lambda: _get("HACKATHON_WEATHER_BASE_URL"))

    vision_provider: str = field(default_factory=lambda: _get("VISION_PROVIDER", "local_heuristic").lower())
    vision_fallback_chain: List[str] = field(
        default_factory=lambda: _get_list("VISION_FALLBACK_CHAIN", "llm_vision,local_heuristic,mock")
    )

    recommendation_provider: str = field(
        default_factory=lambda: _get("RECOMMENDATION_PROVIDER", "template").lower()
    )
    recommendation_fallback_chain: List[str] = field(
        default_factory=lambda: _get_list("RECOMMENDATION_FALLBACK_CHAIN", "llm,template")
    )

    max_upload_mb: int = field(default_factory=lambda: _get_int("MAX_UPLOAD_MB", 8))
    tool_timeout_seconds: int = field(default_factory=lambda: _get_int("TOOL_TIMEOUT_SECONDS", 12))
    agent_max_iterations: int = field(default_factory=lambda: _get_int("AGENT_MAX_ITERATIONS", 6))

    db_path: str = field(default_factory=lambda: _get("DB_PATH", "data/runs.sqlite3"))
    log_dir: str = field(default_factory=lambda: _get("LOG_DIR", "logs"))

    def tool_enabled(self, tool_name: str) -> bool:
        """Feature flag per tool. Core tools default on, optional tools default off."""
        core_defaults = {
            "vision": True,
            "sensors": True,
            "weather": True,
            "risk": True,
            "recommendation": True,
        }
        default = core_defaults.get(tool_name, False)
        return _get_bool(f"TOOL_{tool_name.upper()}_ENABLED", default)

    @property
    def offline_first(self) -> bool:
        """True when the agent should avoid network calls unless explicitly asked."""
        return self.demo_mode or self.environment == "demo"

    def public_summary(self) -> dict:
        """Config snapshot with no secret values — safe to log / show in UI."""
        return {
            "environment": self.environment,
            "demo_mode": self.demo_mode,
            "demo_judge_mode": self.demo_judge_mode,
            "llm_provider": self.llm_provider,
            "weather_provider": self.weather_provider,
            "vision_provider": self.vision_provider,
            "recommendation_provider": self.recommendation_provider,
            "anthropic_key": redact(get_secret("ANTHROPIC_API_KEY")),
            "openai_key": redact(get_secret("OPENAI_API_KEY")),
            "agent_max_iterations": self.agent_max_iterations,
            "tool_timeout_seconds": self.tool_timeout_seconds,
        }


settings = Settings()

__all__ = ["settings", "Settings", "get_secret", "has_secret", "redact", "PROJECT_ROOT", "_SECRET_KEYS"]

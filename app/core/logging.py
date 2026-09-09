"""Lightweight structured logging + per-run observability.

- ``get_logger()`` returns a stdlib logger that scrubs credential-looking text.
- ``RunLogger`` appends one JSON record per agent run to a JSONL file and to
  the SQLite ``runs`` table (see ``app/data/database.py``).
"""
from __future__ import annotations

import json
import logging
import time
import uuid

from typing import Any, Dict, List, Optional

from app.core.config import PROJECT_ROOT, settings
from app.core.security import scrub_secrets


class _ScrubFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        if isinstance(record.msg, str):
            record.msg = scrub_secrets(record.msg)
        return True


_LOGGER_CACHE: Dict[str, logging.Logger] = {}


def get_logger(name: str = "sahel") -> logging.Logger:
    if name in _LOGGER_CACHE:
        return _LOGGER_CACHE[name]
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s | %(message)s"))
        handler.addFilter(_ScrubFilter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    _LOGGER_CACHE[name] = logger
    return logger


class RunLogger:
    """Records a single agent run for the "Run Details" view and the benchmark."""

    def __init__(self, session_id: Optional[str] = None) -> None:
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self.run_id = uuid.uuid4().hex[:12]
        self._log_dir = PROJECT_ROOT / settings.log_dir
        self._logger = get_logger("sahel.run")

    def write(
        self,
        *,
        scenario_id: Optional[str],
        reasoning_mode: str,
        tools_used: List[str],
        provider_map: Dict[str, str],
        execution_ms: float,
        success: bool,
        degraded: bool,
        errors: List[str],
        trace_lines: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        record: Dict[str, Any] = {
            "run_id": self.run_id,
            "session_id": self.session_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            "environment": settings.environment,
            "scenario_id": scenario_id,
            "reasoning_mode": reasoning_mode,
            "tools_used": tools_used,
            "providers": provider_map,
            "execution_ms": round(execution_ms, 1),
            "success": success,
            "degraded": degraded,
            "errors": [scrub_secrets(e) for e in errors],
            "trace": trace_lines or [],
        }

        # JSONL sink (best-effort — never break a run because logging failed).
        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            with (self._log_dir / "runs.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:  # pragma: no cover
            self._logger.warning("could not write runs.jsonl: %s", exc)

        # SQLite sink (best-effort).
        try:
            from app.data.database import save_run

            save_run(record)
        except Exception as exc:  # noqa: BLE001  pragma: no cover
            self._logger.warning("could not persist run to sqlite: %s", exc)

        return record

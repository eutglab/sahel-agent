"""Trace primitives.

The models live in ``app.core.schemas`` (single source of truth). This module
re-exports them and adds a tiny factory so call sites can do::

    from app.core.trace import new_trace
"""
from __future__ import annotations

from app.core.schemas import AgentTrace, ToolCallRecord, TraceEvent

__all__ = ["AgentTrace", "ToolCallRecord", "TraceEvent", "new_trace"]


def new_trace() -> AgentTrace:
    return AgentTrace()

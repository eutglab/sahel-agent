"""Provider-agnostic LLM interface.

Business code depends ONLY on ``LLMClient``. Concrete SDKs live in
``app/llm/providers/``. Select with ``LLM_PROVIDER`` env var.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.schemas import HealthStatus, MaturityStatus


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: Dict[str, Any]


@dataclass
class ToolInvocation:
    """A tool call the model asked for."""
    name: str
    arguments: Dict[str, Any]


@dataclass
class LLMResponse:
    text: str = ""
    tool_calls: List[ToolInvocation] = field(default_factory=list)
    raw: Optional[Any] = None
    finish_reason: str = "stop"


class LLMClient(abc.ABC):
    name: str = "base"
    status: MaturityStatus = MaturityStatus.IMPLEMENTED

    @abc.abstractmethod
    def complete(self, system: str, user: str, *, max_tokens: int = 800) -> LLMResponse:
        ...

    @abc.abstractmethod
    def complete_with_tools(
        self,
        system: str,
        user: str,
        tools: List[ToolSpec],
        *,
        tool_results: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 900,
    ) -> LLMResponse:
        ...

    @abc.abstractmethod
    def analyze_image(self, image_bytes: bytes, prompt: str) -> LLMResponse:
        ...

    @abc.abstractmethod
    def health_check(self) -> HealthStatus:
        ...

    @property
    def is_mock(self) -> bool:
        return self.status == MaturityStatus.MOCKED

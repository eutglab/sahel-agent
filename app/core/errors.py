"""Typed exceptions for SAHEL Agent.

Every failure mode has a named exception so the agent loop and the fallback
chains can react precisely instead of catching bare ``Exception``.
"""
from __future__ import annotations


class SahelError(Exception):
    """Base class for all SAHEL Agent errors."""


class ConfigError(SahelError):
    """Configuration is missing or invalid."""


class ToolError(SahelError):
    """Generic tool failure."""


class ToolInputError(ToolError):
    """Input did not satisfy the tool's input schema."""


class ToolOutputError(ToolError):
    """A provider returned data that failed the tool's output schema."""


class ProviderError(SahelError):
    """A provider (external service adapter) failed to produce a result."""


class ProviderTimeout(ProviderError):
    """A provider exceeded its time budget."""


class ProviderUnavailable(ProviderError):
    """A provider is unreachable, unauthenticated, or out of quota."""


class NotIntegratedError(SahelError):
    """Tool/provider is declared (INTEGRATION_READY / FUTURE) but not wired.

    Raised on purpose so the agent never fabricates data for a capability that
    has not actually been connected.
    """


class FallbackExhausted(SahelError):
    """Every provider in a fallback chain failed."""


class AgentError(SahelError):
    """The agent loop could not complete."""

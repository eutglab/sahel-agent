"""OpenRouter LLM provider — unit tests with a fake in-memory `openai` SDK.

No real network call is ever made here (the `openai` package isn't even a
hard dependency of this repo — see requirements.txt). A minimal fake module is
injected into ``sys.modules`` so ``OpenAILLMClient``'s lazy
``from openai import OpenAI`` succeeds, and its ``chat.completions.create`` is
fully controlled per test.

Covers the contract described in docs/providers.md: missing key / missing
model, a successful call, timeout / HTTP / malformed / empty responses, no
secret leakage, and that the agent falls back to the deterministic planner
(this project's "local" LLM fallback — see app/agent/agent.py `use_llm`)
when OpenRouter fails or is unconfigured.
"""
from __future__ import annotations

import importlib.machinery
import sys
import types

import pytest

from app.core.errors import ProviderTimeout, ProviderUnavailable


def _fake_settings(*, model: str = "", timeout: int = 20,
                    base_url: str = "https://openrouter.ai/api/v1") -> types.SimpleNamespace:
    return types.SimpleNamespace(
        openrouter_base_url=base_url,
        openrouter_model=model,
        openrouter_timeout_seconds=timeout,
    )


class _Msg:
    def __init__(self, content=None):
        self.content = content
        self.tool_calls = []


class _Choice:
    def __init__(self, message):
        self.message = message


class _Resp:
    def __init__(self, choices):
        self.choices = choices


def _ok_response(text: str = "hello") -> _Resp:
    return _Resp([_Choice(_Msg(content=text))])


def _install_fake_openai(monkeypatch) -> types.SimpleNamespace:
    """Install a fake `openai` module and return a controller whose
    `.response` / `.exception` decide what `chat.completions.create` does."""
    controller = types.SimpleNamespace(response=None, exception=None, last_kwargs=None)

    class FakeAPIError(Exception):
        pass

    class FakeAPITimeoutError(FakeAPIError):
        pass

    class FakeAuthenticationError(FakeAPIError):
        pass

    class FakeRateLimitError(FakeAPIError):
        pass

    class FakeAPIConnectionError(FakeAPIError):
        pass

    class FakeAPIStatusError(FakeAPIError):
        def __init__(self, message="error", status_code=500):
            super().__init__(message)
            self.status_code = status_code

    class _Completions:
        def create(self, **kwargs):
            controller.last_kwargs = kwargs
            if controller.exception is not None:
                raise controller.exception
            return controller.response

    class _Chat:
        def __init__(self):
            self.completions = _Completions()

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.chat = _Chat()

    fake_module = types.ModuleType("openai")
    # A real `import openai` always has a resolvable __spec__; without one,
    # importlib.util.find_spec("openai") raises instead of returning a value
    # (see OpenRouterLLMClient.health_check()) — set it so the fake behaves
    # like a real installed package.
    fake_module.__spec__ = importlib.machinery.ModuleSpec("openai", loader=None)
    fake_module.OpenAI = FakeOpenAI
    fake_module.APIError = FakeAPIError
    fake_module.APITimeoutError = FakeAPITimeoutError
    fake_module.AuthenticationError = FakeAuthenticationError
    fake_module.RateLimitError = FakeRateLimitError
    fake_module.APIConnectionError = FakeAPIConnectionError
    fake_module.APIStatusError = FakeAPIStatusError
    monkeypatch.setitem(sys.modules, "openai", fake_module)
    controller.module = fake_module
    return controller


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

def test_missing_api_key_raises_provider_unavailable(monkeypatch):
    from app.llm.providers.openrouter import OpenRouterLLMClient

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("app.llm.providers.openrouter.settings", _fake_settings(model="openai/gpt-4o-mini"))
    client = OpenRouterLLMClient()
    with pytest.raises(ProviderUnavailable):
        client._client()


def test_missing_model_raises_provider_unavailable(monkeypatch):
    from app.llm.providers.openrouter import OpenRouterLLMClient

    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key-for-tests")
    monkeypatch.setattr("app.llm.providers.openrouter.settings", _fake_settings(model=""))
    client = OpenRouterLLMClient()
    with pytest.raises(ProviderUnavailable):
        client._client()


def test_valid_configuration_health_check_ready_no_secret_leakage(monkeypatch):
    from app.llm.providers.openrouter import OpenRouterLLMClient

    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key-for-tests")
    monkeypatch.setattr("app.llm.providers.openrouter.settings", _fake_settings(model="openai/gpt-4o-mini"))
    _install_fake_openai(monkeypatch)
    client = OpenRouterLLMClient()
    health = client.health_check()
    assert health.state.value == "READY"
    assert "fake-key-for-tests" not in health.detail
    assert "fake-key-for-tests" not in str(health.model_dump())


def test_invalid_configuration_health_check_warning(monkeypatch):
    from app.llm.providers.openrouter import OpenRouterLLMClient

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("app.llm.providers.openrouter.settings", _fake_settings())
    client = OpenRouterLLMClient()
    health = client.health_check()
    assert health.state.value == "WARNING"


# --------------------------------------------------------------------------- #
# Calls: success + every failure mode the fallback contract must survive
# --------------------------------------------------------------------------- #

def _ready_client(monkeypatch):
    from app.llm.providers.openrouter import OpenRouterLLMClient

    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key-for-tests")
    monkeypatch.setattr("app.llm.providers.openrouter.settings", _fake_settings(model="openai/gpt-4o-mini"))
    return OpenRouterLLMClient()


def test_successful_completion(monkeypatch):
    client = _ready_client(monkeypatch)
    controller = _install_fake_openai(monkeypatch)
    controller.response = _ok_response("water stress is moderate")
    resp = client.complete("system", "user")
    assert resp.text == "water stress is moderate"


def test_timeout_raises_provider_timeout(monkeypatch):
    client = _ready_client(monkeypatch)
    controller = _install_fake_openai(monkeypatch)
    controller.exception = controller.module.APITimeoutError("timed out")
    with pytest.raises(ProviderTimeout):
        client.complete("system", "user")


def test_http_error_raises_provider_unavailable(monkeypatch):
    client = _ready_client(monkeypatch)
    controller = _install_fake_openai(monkeypatch)
    controller.exception = controller.module.APIStatusError("rate limited", status_code=429)
    with pytest.raises(ProviderUnavailable):
        client.complete("system", "user")


def test_authentication_error_raises_provider_unavailable_no_key_in_message(monkeypatch):
    client = _ready_client(monkeypatch)
    controller = _install_fake_openai(monkeypatch)
    controller.exception = controller.module.AuthenticationError("invalid api key: fake-key-for-tests")
    with pytest.raises(ProviderUnavailable) as exc_info:
        client.complete("system", "user")
    assert "fake-key-for-tests" not in str(exc_info.value)


def test_malformed_response_raises_provider_unavailable(monkeypatch):
    client = _ready_client(monkeypatch)
    controller = _install_fake_openai(monkeypatch)
    controller.response = _Resp([])  # no choices at all
    with pytest.raises(ProviderUnavailable):
        client.complete("system", "user")


def test_empty_response_does_not_raise(monkeypatch):
    client = _ready_client(monkeypatch)
    controller = _install_fake_openai(monkeypatch)
    controller.response = _ok_response(text=None)
    resp = client.complete("system", "user")
    assert resp.text == ""


# --------------------------------------------------------------------------- #
# Agent-level fallback: OpenRouter failing must never break an analysis.
# "Local fallback" in this codebase is the deterministic planner (L2) — see
# app/agent/agent.py `use_llm` / docs/architecture.md section 4.
# --------------------------------------------------------------------------- #

def test_agent_falls_back_to_deterministic_when_openrouter_unconfigured(monkeypatch):
    import types as _types

    from app.agent.agent import SahelAgent
    from app.core.schemas import AgentInput, Location, SensorReadings
    from app.llm.providers.openrouter import OpenRouterLLMClient

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("app.llm.providers.openrouter.settings", _fake_settings())
    fake_agent_settings = _types.SimpleNamespace(offline_first=False, agent_max_iterations=6)
    monkeypatch.setattr("app.agent.agent.settings", fake_agent_settings)

    agent = SahelAgent(llm=OpenRouterLLMClient())
    ai = AgentInput(
        sensors=SensorReadings(temperature_c=37, soil_moisture_pct=18, growth_stage="flowering"),
        location=Location(label="Fictional Site Alpha", latitude=14.5, longitude=-4.2),
    )
    result = agent.analyze(ai)
    assert result.reasoning_mode == "deterministic"
    assert result.recommendation is not None


def test_agent_falls_back_to_mock_style_result_when_openrouter_errors_mid_call(monkeypatch):
    """Key+model ARE configured but the live call fails (e.g. quota) —
    same guarantee: the analysis still completes via the deterministic path."""
    import types as _types

    from app.agent.agent import SahelAgent
    from app.core.schemas import AgentInput, Location, SensorReadings

    client = _ready_client(monkeypatch)
    controller = _install_fake_openai(monkeypatch)
    controller.exception = controller.module.RateLimitError("quota exceeded")

    fake_agent_settings = _types.SimpleNamespace(offline_first=False, agent_max_iterations=6)
    monkeypatch.setattr("app.agent.agent.settings", fake_agent_settings)

    agent = SahelAgent(llm=client)
    ai = AgentInput(
        sensors=SensorReadings(temperature_c=37, soil_moisture_pct=18, growth_stage="flowering"),
        location=Location(label="Fictional Site Alpha", latitude=14.5, longitude=-4.2),
    )
    result = agent.analyze(ai)
    assert result.recommendation is not None
    assert result.degraded is True

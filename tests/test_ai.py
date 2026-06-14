import pytest
from conftest import FakeLLM

from olx_finder.ai import Message, RateLimitError, get_client
from olx_finder.config import Settings
from olx_finder.models import OfferFinderError


def test_no_keys_raises_with_setup_hint():
    with pytest.raises(OfferFinderError) as exc:
        get_client(Settings())
    assert "GEMINI_API_KEY" in str(exc.value)


def test_prefers_openai_when_both_keys_present():
    client = get_client(Settings(gemini_api_key="g", openai_api_key="o"))
    assert client.name == "OpenAI"


def test_explicit_provider_overrides_auto_detect():
    client = get_client(Settings(provider="openai", gemini_api_key="g", openai_api_key="o"))
    assert client.name == "OpenAI"


def test_explicit_provider_without_its_key_raises():
    with pytest.raises(OfferFinderError):
        get_client(Settings(provider="gemini"))


def test_complete_retries_on_rate_limit(monkeypatch):
    sleeps = []
    monkeypatch.setattr("olx_finder.ai.time.sleep", sleeps.append)
    fake = FakeLLM([RateLimitError("slow"), RateLimitError("slow"), "ok"])

    assert fake.complete([Message("user", "hi")]) == "ok"
    assert sleeps == [5, 10]


def test_complete_gives_up_after_three_attempts(monkeypatch):
    monkeypatch.setattr("olx_finder.ai.time.sleep", lambda _: None)
    fake = FakeLLM([RateLimitError("1"), RateLimitError("2"), RateLimitError("3")])

    with pytest.raises(RateLimitError):
        fake.complete([Message("user", "hi")])
    assert len(fake.calls) == 3

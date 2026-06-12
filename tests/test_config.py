import pytest

from olx_finder.config import Settings
from olx_finder.models import OfferFinderError

VARIABLES = ["LLM_PROVIDER", "OPENAI_API_KEY", "OPENAI_MODEL", "GEMINI_API_KEY",
             "GEMINI_MODEL", "MAX_OFFERS", "MAX_PAGES", "HEADLESS"]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in VARIABLES:
        monkeypatch.delenv(name, raising=False)


def test_defaults_with_empty_env():
    settings = Settings.from_env()
    assert settings.provider is None
    assert settings.gemini_api_key is None
    assert settings.max_offers is None
    assert settings.headless is True


def test_reads_overrides_from_env(monkeypatch):
    monkeypatch.setenv("MAX_OFFERS", "7")
    monkeypatch.setenv("HEADLESS", "false")
    monkeypatch.setenv("GEMINI_API_KEY", "g-key")

    settings = Settings.from_env()
    assert settings.max_offers == 7
    assert settings.headless is False
    assert settings.gemini_api_key == "g-key"


def test_invalid_number_raises(monkeypatch):
    monkeypatch.setenv("MAX_OFFERS", "lots")
    with pytest.raises(OfferFinderError):
        Settings.from_env()

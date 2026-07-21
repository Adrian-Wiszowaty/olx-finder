import os
from dataclasses import dataclass

from olx_finder.models import OfferFinderError

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class Settings:
    provider: str | None = None
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    max_pages: int = 100
    headless: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            provider=_clean(os.getenv("LLM_PROVIDER")),
            openai_api_key=_clean(os.getenv("OPENAI_API_KEY")),
            openai_model=_clean(os.getenv("OPENAI_MODEL")) or cls.openai_model,
            gemini_api_key=_clean(os.getenv("GEMINI_API_KEY")),
            gemini_model=_clean(os.getenv("GEMINI_MODEL")) or cls.gemini_model,
            max_pages=_int("MAX_PAGES", cls.max_pages),
            headless=os.getenv("HEADLESS", "").strip().lower() not in ("false", "0", "no"),
        )


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def _int(name: str, default: int) -> int:
    value = _optional_int(name)
    return default if value is None else value


def _optional_int(name: str) -> int | None:
    raw = _clean(os.getenv(name))
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        raise OfferFinderError(f"Zmienna {name} musi być liczbą (jest: {raw!r}).") from None

import os
from dataclasses import dataclass

from olx_finder.models import OfferFinderError

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class Settings:
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    max_offers: int = 20
    max_pages: int = 5
    headless: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            openai_api_key=_clean(os.getenv("OPENAI_API_KEY")),
            openai_model=_clean(os.getenv("OPENAI_MODEL")) or cls.openai_model,
            max_offers=_int("MAX_OFFERS", cls.max_offers),
            max_pages=_int("MAX_PAGES", cls.max_pages),
            headless=os.getenv("HEADLESS", "").strip().lower() not in ("false", "0", "no"),
        )


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def _int(name: str, default: int) -> int:
    raw = _clean(os.getenv(name))
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        raise OfferFinderError(f"Zmienna {name} musi być liczbą (jest: {raw!r}).") from None

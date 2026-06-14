import time
from dataclasses import dataclass

from olx_finder.config import Settings
from olx_finder.models import OfferFinderError

MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 5


class RateLimitError(OfferFinderError):
    pass


class InsufficientQuotaError(OfferFinderError):
    pass


@dataclass
class Message:
    role: str
    content: str


class LLMClient:
    name = "LLM"

    def __init__(self, model):
        self.model = model

    def complete(self, messages, temperature=0.2):
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                return self._chat(messages, temperature)
            except OfferFinderError as error:
                if not isinstance(error, RateLimitError) or attempt == MAX_ATTEMPTS:
                    raise
            except Exception:
                if attempt == MAX_ATTEMPTS:
                    raise
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    def _chat(self, messages, temperature):
        raise NotImplementedError


class OpenAIClient(LLMClient):
    name = "OpenAI"

    def __init__(self, api_key, model):
        super().__init__(model)
        import openai

        self._openai = openai
        self._client = openai.OpenAI(api_key=api_key)

    def _chat(self, messages, temperature):
        try:
            reply = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=temperature,
            )
        except self._openai.RateLimitError as error:
            if getattr(error, "code", None) == "insufficient_quota":
                raise InsufficientQuotaError(
                    "Brak środków na koncie OpenAI. Doładuj konto albo użyj "
                    "darmowego klucza Gemini: https://aistudio.google.com/apikey"
                ) from error
            raise RateLimitError(str(error)) from error
        except self._openai.OpenAIError as error:
            raise OfferFinderError(f"Błąd OpenAI: {error}") from error
        return (reply.choices[0].message.content or "").strip()


class GeminiClient(LLMClient):
    name = "Gemini"

    def __init__(self, api_key, model):
        super().__init__(model)
        from google import genai
        from google.genai import errors, types

        self._types = types
        self._errors = errors
        self._client = genai.Client(api_key=api_key)

    def _chat(self, messages, temperature):
        types = self._types
        system = "\n\n".join(m.content for m in messages if m.role == "system")
        contents = [
            types.Content(
                role="user" if m.role == "user" else "model",
                parts=[types.Part(text=m.content)],
            )
            for m in messages
            if m.role != "system"
        ]
        config = types.GenerateContentConfig(
            temperature=temperature, system_instruction=system or None
        )
        try:
            reply = self._client.models.generate_content(
                model=self.model, contents=contents, config=config
            )
        except self._errors.APIError as error:
            if error.code in (429, 503):
                raise RateLimitError(str(error)) from error
            raise OfferFinderError(f"Błąd Gemini: {error}") from error
        return (reply.text or "").strip()


def get_client(settings: Settings):
    provider = (settings.provider or "").lower()
    if not provider:
        if not settings.gemini_api_key and not settings.openai_api_key:
            raise OfferFinderError(
                "Nie znaleziono klucza API. Wpisz w pliku .env GEMINI_API_KEY "
                "(darmowy: https://aistudio.google.com/apikey) albo OPENAI_API_KEY."
            )
        provider = "openai" if settings.openai_api_key else "gemini"

    if provider == "gemini":
        if not settings.gemini_api_key:
            raise OfferFinderError("Brak klucza GEMINI_API_KEY (ustaw go w pliku .env).")
        return GeminiClient(settings.gemini_api_key, settings.gemini_model)
    if provider == "openai":
        if not settings.openai_api_key:
            raise OfferFinderError("Brak klucza OPENAI_API_KEY (ustaw go w pliku .env).")
        return OpenAIClient(settings.openai_api_key, settings.openai_model)
    raise OfferFinderError(f"Nieznany dostawca LLM: {provider!r} (dostępne: gemini, openai).")

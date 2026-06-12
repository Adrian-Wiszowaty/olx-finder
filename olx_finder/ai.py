import time
from dataclasses import dataclass

from olx_finder.config import Settings
from olx_finder.models import OfferFinderError


class RateLimitError(OfferFinderError):
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
        for attempt in range(2):
            try:
                return self._chat(messages, temperature)
            except RateLimitError:
                time.sleep(5 * (attempt + 1))
        return self._chat(messages, temperature)

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
                raise OfferFinderError("Brak środków na koncie OpenAI — doładuj konto.") from error
            raise RateLimitError(str(error)) from error
        except self._openai.OpenAIError as error:
            raise OfferFinderError(f"Błąd OpenAI: {error}") from error
        return (reply.choices[0].message.content or "").strip()


def get_client(settings: Settings):
    if not settings.openai_api_key:
        raise OfferFinderError("Brak klucza OPENAI_API_KEY (ustaw go w pliku .env).")
    return OpenAIClient(settings.openai_api_key, settings.openai_model)

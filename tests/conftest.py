import pytest

from olx_finder.ai import LLMClient, Message
from olx_finder.models import Offer


class FakeLLM(LLMClient):
    name = "Fake"

    def __init__(self, responses):
        super().__init__("fake")
        self.responses = list(responses)
        self.calls = []

    def _chat(self, messages, temperature):
        self.calls.append(list(messages))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture
def make_offer():
    def _make(i):
        return Offer(f"Offer {i}", f"{i}00 zł", f"https://www.olx.pl/oferta/{i}", f"Description {i}")

    return _make

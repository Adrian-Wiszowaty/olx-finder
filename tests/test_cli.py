import olx_finder.cli as cli
from conftest import FakeLLM
from olx_finder.ai import InsufficientQuotaError, Message


def test_fallback_switches_to_gemini_then_stays_on_it():
    switches = []
    primary = FakeLLM([InsufficientQuotaError("no funds")])
    fallback = FakeLLM(["from fallback", "second answer"])
    client = cli._FallbackClient(primary, fallback, on_switch=lambda: switches.append(1))

    assert client.complete([Message("user", "hi")]) == "from fallback"
    assert client.complete([Message("user", "again")]) == "second answer"

    assert switches == [1]
    assert len(primary.calls) == 1

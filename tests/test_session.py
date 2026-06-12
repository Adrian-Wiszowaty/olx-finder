import pytest
from conftest import FakeLLM

from olx_finder.analyzer import OfferAnalyzer
from olx_finder.models import AnalysisPlan, OfferFinderError


def _session(fake, make_offer):
    offer = make_offer(1)
    offer.spec = {"cpu": "i5"}
    return OfferAnalyzer(fake).start_session("gaming pc", AnalysisPlan(), [offer])


def test_session_remembers_the_conversation(make_offer):
    fake = FakeLLM(["first ranking", "follow-up answer"])
    session = _session(fake, make_offer)

    assert session.ranking(top_n=5) == "first ranking"
    assert session.ask("show top 10") == "follow-up answer"

    roles = [m.role for m in fake.calls[1]]
    assert roles == ["system", "user", "assistant", "user"]
    assert "i5" in fake.calls[1][0].content
    assert "gaming pc" in fake.calls[1][0].content


def test_failed_question_is_not_kept_in_history(make_offer):
    fake = FakeLLM(["ranking", OfferFinderError("boom"), "recovered"])
    session = _session(fake, make_offer)
    session.ranking()

    with pytest.raises(OfferFinderError):
        session.ask("broken")
    assert session.ask("again") == "recovered"

    assert "broken" not in [m.content for m in fake.calls[-1]]

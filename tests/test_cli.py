import olx_finder.cli as cli
from olx_finder.config import Settings


def _fake_prompt(monkeypatch, answer):
    defaults = []

    def ask(*args, **kwargs):
        defaults.append(kwargs.get("default"))
        return answer

    monkeypatch.setattr(cli.Prompt, "ask", ask)
    return defaults


def test_no_prompt_when_user_set_an_explicit_limit(monkeypatch):
    defaults = _fake_prompt(monkeypatch, "5")
    listings = list(range(100))

    result = cli._maybe_limit(listings, Settings(max_offers=10))

    assert result == listings
    assert defaults == []


def test_no_prompt_for_small_result_sets(monkeypatch):
    defaults = _fake_prompt(monkeypatch, "5")
    listings = list(range(cli.LARGE_RESULT_SET))

    assert cli._maybe_limit(listings, Settings()) == listings
    assert defaults == []


def test_large_set_is_capped_to_the_users_choice(monkeypatch):
    _fake_prompt(monkeypatch, "5")
    result = cli._maybe_limit(list(range(830)), Settings())
    assert result == list(range(5))


def test_large_set_keeps_everything_when_answer_is_not_a_number(monkeypatch):
    _fake_prompt(monkeypatch, "wszystkie")
    listings = list(range(830))
    assert cli._maybe_limit(listings, Settings()) == listings

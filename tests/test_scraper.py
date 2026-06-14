import pytest

from olx_finder.config import Settings
from olx_finder.models import OfferFinderError
from olx_finder.scraper import _page_param, _with_page, get_scraper


def test_with_page_adds_the_page_parameter():
    assert _with_page("https://www.olx.pl/komputery/", 2) == "https://www.olx.pl/komputery/?page=2"


def test_with_page_replaces_an_existing_page_parameter():
    url = "https://www.olx.pl/komputery/?q=gaming&page=7"
    assert _with_page(url, 3) == "https://www.olx.pl/komputery/?q=gaming&page=3"


def test_page_param_reads_the_page_number():
    assert _page_param("https://www.olx.pl/komputery/?q=gaming&page=4") == 4


def test_page_param_returns_none_without_a_page():
    assert _page_param("https://www.olx.pl/komputery/?q=gaming") is None


def test_get_scraper_rejects_other_sites():
    with pytest.raises(OfferFinderError):
        get_scraper("https://allegro.pl/kategoria/laptopy", Settings())


def test_get_scraper_rejects_lookalike_domain():
    with pytest.raises(OfferFinderError):
        get_scraper("https://notolx.pl/elektronika", Settings())

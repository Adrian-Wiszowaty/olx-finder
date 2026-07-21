import logging
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from olx_finder.config import USER_AGENT, Settings
from olx_finder.models import Offer, OfferFinderError

log = logging.getLogger(__name__)

CARD_SELECTOR = "div[data-cy='l-card']"


class OlxScraper:
    def __init__(self, headless: bool = True):
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--lang=pl-PL")
        options.add_argument(f"user-agent={USER_AGENT}")
        if headless:
            options.add_argument("--headless=new")
        try:
            self.driver = webdriver.Chrome(options=options)
        except WebDriverException as error:
            raise OfferFinderError(
                "Nie udało się uruchomić Chrome — sprawdź, czy przeglądarka jest zainstalowana."
            ) from error

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        try:
            self.driver.quit()
        except WebDriverException:
            pass

    def collect_listings(self, search_url, max_pages=100, on_page=None) -> list[Offer]:
        offers, seen = [], set()
        total_pages = None
        for page in range(1, max_pages + 1):
            if not self._open_results(_with_page(search_url, page)):
                break
            if page == 1:
                total_pages = self._total_pages()
            if total_pages is not None and page > total_pages:
                total_pages = None

            found = 0
            for element in self.driver.find_elements(By.CSS_SELECTOR, CARD_SELECTOR):
                offer = _parse_card(element)
                if offer is None or offer.url in seen:
                    continue
                seen.add(offer.url)
                offers.append(offer)
                found += 1

            if found and on_page:
                on_page(page, len(offers), total_pages)
            if not found:
                break
        return offers

    def add_descriptions(self, offers: list[Offer], on_offer=None) -> list[Offer]:
        for index, offer in enumerate(offers, 1):
            offer.description = self._fetch_description(offer.url)
            if on_offer:
                on_offer(index, len(offers))
        return offers

    def _open_results(self, url: str) -> bool:
        self.driver.get(url)
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, CARD_SELECTOR))
            )
            return True
        except TimeoutException:
            return False

    def _total_pages(self) -> int | None:
        try:
            links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='page=']")
        except WebDriverException:
            return None
        pages = [page for link in links if (page := _page_param(link.get_attribute("href") or ""))]
        return max(pages, default=None)

    def _fetch_description(self, url: str) -> str:
        try:
            self.driver.get(url)
            element = WebDriverWait(self.driver, 6).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-cy='ad_description']"))
            )
            return element.text.strip()
        except (TimeoutException, WebDriverException):
            log.info("No description found for %s", url)
            return ""


def get_scraper(url: str, settings: Settings) -> OlxScraper:
    host = (urlsplit(url).hostname or "").lower()
    if host == "olx.pl" or host.endswith(".olx.pl"):
        return OlxScraper(headless=settings.headless)
    raise OfferFinderError("Na razie obsługiwany jest tylko serwis OLX (olx.pl).")


def _with_page(url: str, page: int) -> str:
    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != "page"]
    query.append(("page", str(page)))
    return urlunsplit(parts._replace(query=urlencode(query)))


def _page_param(url: str) -> int | None:
    for key, value in parse_qsl(urlsplit(url).query):
        if key == "page" and value.isdigit():
            return int(value)
    return None


def _parse_card(card) -> Offer | None:
    try:
        title = card.find_element(
            By.CSS_SELECTOR, "div[data-testid='ad-card-title'] h4, div[data-testid='ad-card-title'] h6"
        ).text.strip()
        price = card.find_element(By.CSS_SELECTOR, "p[data-testid='ad-price']").text.strip()
        link = card.find_element(By.CSS_SELECTOR, "div[data-testid='ad-card-title'] a")
        url = link.get_attribute("href") or ""
    except WebDriverException:
        return None
    if not title or not url:
        return None
    if not url.startswith("http"):
        url = "https://www.olx.pl" + url
    return Offer(title, price, url)

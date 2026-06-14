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

    def collect_listings(self, search_url, max_offers=None, max_pages=100, on_page=None):
        cards = self._collect_cards(search_url, max_offers, max_pages, on_page)
        return [Offer(title, price, url) for title, price, url in cards]

    def add_descriptions(self, offers, on_offer=None):
        for i, offer in enumerate(offers, 1):
            offer.description = self._description(offer.url)
            if on_offer:
                on_offer(i, len(offers))
        return offers

    def _collect_cards(self, search_url, max_offers, max_pages, on_page):
        cards, seen = [], set()
        total_pages = None
        for page in range(1, max_pages + 1):
            self.driver.get(_with_page(search_url, page))
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-cy='l-card']"))
                )
            except TimeoutException:
                break
            if page == 1:
                total_pages = self._total_pages()
            if total_pages is not None and page > total_pages:
                total_pages = None
            new = 0
            for card in self.driver.find_elements(By.CSS_SELECTOR, "div[data-cy='l-card']"):
                parsed = _parse_card(card)
                if parsed is None or parsed[2] in seen:
                    continue
                seen.add(parsed[2])
                cards.append(parsed)
                new += 1
                if max_offers is not None and len(cards) >= max_offers:
                    break
            if new > 0 and on_page:
                on_page(page, len(cards), total_pages)
            if new == 0 or (max_offers is not None and len(cards) >= max_offers):
                break
        return cards

    def _total_pages(self):
        try:
            links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='page=']")
            pages = []
            for link in links:
                href = link.get_attribute("href") or ""
                for k, v in parse_qsl(urlsplit(href).query):
                    if k == "page":
                        try:
                            pages.append(int(v))
                        except ValueError:
                            pass
            return max(pages) if pages else None
        except WebDriverException:
            return None

    def _description(self, url):
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
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "page"]
    query.append(("page", str(page)))
    return urlunsplit(parts._replace(query=urlencode(query)))


def _parse_card(card):
    try:
        title = card.find_element(
            By.CSS_SELECTOR, "div[data-cy='ad-card-title'] h4, div[data-cy='ad-card-title'] h6"
        ).text.strip()
        price = card.find_element(By.CSS_SELECTOR, "p[data-testid='ad-price']").text.strip()
        link = card.find_element(By.CSS_SELECTOR, "div[data-cy='ad-card-title'] a")
        url = link.get_attribute("href") or ""
    except WebDriverException:
        return None
    if not title or not url:
        return None
    if not url.startswith("http"):
        url = "https://www.olx.pl" + url
    return title, price, url

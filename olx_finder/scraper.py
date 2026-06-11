from typing import List, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from olx_finder.config import Config


class Scraper:
    def __init__(self, headless: bool = True, base_url: str = None, user_agent: str = None) -> None:
        print("Szukanie ofert...")
        self.BASE_URL: str = base_url or Config.OLX_URL
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(
            f"user-agent={user_agent or Config.OLX_USER_AGENT}"
        )
        if headless:
            options.add_argument("--headless=new")

        service = Service(ChromeDriverManager().install())
        self.driver: webdriver.Chrome = webdriver.Chrome(service=service, options=options)

    def close(self) -> None:
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def __del__(self):
        self.close()

    def __enter__(self) -> 'Scraper':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _extract_offer_details(self, link: str) -> str:
        self.driver.execute_script("window.open('about:blank','_blank');")
        self.driver.switch_to.window(self.driver.window_handles[-1])
        self.driver.get(link)

        desc = ""
        try:
            desc_el = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-cy='ad_description']"))
            )
            desc = desc_el.text.strip()
        except TimeoutException:
            pass
        finally:
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])

        return desc

    def fetch_offers(self) -> List[Dict[str, Any]]:
        all_offers: List[Dict[str, Any]] = []
        page = 1

        try:
            while True:
                url = f"{self.BASE_URL}&page={page}"
                self.driver.get(url)

                try:
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-cy='l-card']"))
                    )
                except TimeoutException:
                    print(f"Brak ofert na stronie {page}.")
                    break

                offers = self.driver.find_elements(By.CSS_SELECTOR, "div[data-cy='l-card']")
                print(f"Strona {page} → znaleziono {len(offers)} ofert.")

                if not offers:
                    break

                for offer in offers:
                    try:
                        title_el = offer.find_element(By.CSS_SELECTOR,
                                                     "div[data-cy='ad-card-title'] h4, "
                                                     "div[data-cy='ad-card-title'] h6")
                        price_el = offer.find_element(By.CSS_SELECTOR, "p[data-testid='ad-price']")
                        link_el = offer.find_element(By.CSS_SELECTOR, "div[data-cy='ad-card-title'] a")

                        title = title_el.text.strip()
                        price = price_el.text.strip()
                        link = link_el.get_attribute("href")
                        if not link.startswith("http"):
                            link = "https://www.olx.pl" + link

                        desc = self._extract_offer_details(link)

                        all_offers.append({
                            "title": title,
                            "price": price,
                            "link": link,
                            "desc": desc,
                        })
                    except Exception:
                        print("Nie udało się odczytać ofert:")
                        print(offer.get_attribute("outerHTML"))
                        continue

                page += 1
        finally:
            while len(self.driver.window_handles) > 1:
                self.driver.switch_to.window(self.driver.window_handles[-1])
                self.driver.close()
            self.driver.quit()
            return all_offers

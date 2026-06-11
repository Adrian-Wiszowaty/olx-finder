from olx_finder.scraper import Scraper
from olx_finder.ai_client import AIClient
from olx_finder.spec_extractor import SpecExtractor
from olx_finder.offer_comparator import OfferComparator


class App:

    def __init__(self) -> None:
        self.scraper: Scraper = Scraper()
        self.ai_client: AIClient = AIClient()
        self.spec_extractor: SpecExtractor = SpecExtractor(self.ai_client)
        self.comparator: OfferComparator = OfferComparator(self.ai_client)

    def run(self) -> None:
        try:
            offers = self.scraper.fetch_offers()

            if not offers:
                print("Nie udało się pobrać ofert.")
                return
            
            print(f"Znaleziono ofert: {len(offers)}")
            print(f"Wyciągam specyfikacje z opisów...")

            results = []
            for offer in offers:
                spec = self.spec_extractor.extract(offer["desc"])
                results.append({**offer, "spec": spec})

            print("Wysyłam do AI podsumowanie ofert...")
            summary = self.comparator.compare(results)
            print("\nNajbardziej opłacalne oferty:")
            print(summary)
        except Exception as e:
            print(f"Wystąpił nieoczekiwany błąd: {e}")


if __name__ == "__main__":
    App().run()

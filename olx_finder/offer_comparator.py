from typing import List, Dict, Any
from olx_finder.ai_client_protocol import AIClientProtocol
from olx_finder.prompts import OFFER_COMPARISON


class OfferComparator:
    def __init__(self, ai_client: AIClientProtocol) -> None:
        self.ai_client: AIClientProtocol = ai_client

    def compare(self, offers: List[Dict[str, Any]]) -> str:
        prompt = OFFER_COMPARISON
        for i, offer in enumerate(offers, 1):
            prompt += (
                f"---\nOferta {i}: {offer['title']}\n"
                f"Cena: {offer['price']}\n"
                f"Link: {offer['link']}\n"
                f"Specyfikacja: {offer['spec']}\n"
            )
        try:
            return self.ai_client.get_completion(
                [{"role": "user", "content": prompt}], temperature=0.2
            )
        except Exception as e:
            return f"Błąd AI: {e}"

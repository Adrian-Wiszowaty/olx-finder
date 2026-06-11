from olx_finder.prompts import SPEC_EXTRACTION
from olx_finder.ai_client_protocol import AIClientProtocol


class SpecExtractor:
    def __init__(self, ai_client: AIClientProtocol) -> None:
        self.ai_client: AIClientProtocol = ai_client

    def extract(self, desc: str) -> str:
        prompt = SPEC_EXTRACTION + desc
        try:
            return self.ai_client.get_completion(
                [{"role": "user", "content": prompt}], temperature=0.2
            )
        except Exception as e:
            return f"Błąd AI: {e}"

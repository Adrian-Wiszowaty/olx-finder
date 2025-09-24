from openai import OpenAI
from config import Config
from typing import Any, List, Dict


class AIClient:
    _instance = None

    def __new__(cls) -> 'AIClient':
        if cls._instance is None:
            cls._instance = super(AIClient, cls).__new__(cls)
            cls._instance.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        return cls._instance

    def get_completion(self, messages: List[Dict[str, Any]], temperature: float = 0) -> str:
    
        response = self.client.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content.strip()

from typing import Protocol, List, Dict, Any


class AIClientProtocol(Protocol):
    def get_completion(self, messages: List[Dict[str, Any]], temperature: float = 0) -> str:
        ...

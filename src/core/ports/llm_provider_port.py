from abc import ABC, abstractmethod
from typing import Any

class LLMProviderPort(ABC):
    @abstractmethod
    def get_llm(self) -> Any:
        pass
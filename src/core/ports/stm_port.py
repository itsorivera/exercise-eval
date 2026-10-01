from abc import ABC, abstractmethod
from typing import Any

class STMProviderPort(ABC):
    @abstractmethod
    def get_state_manager(self) -> Any:
        pass
from abc import ABC, abstractmethod
from typing import Any

class AgentPort(ABC):
    @abstractmethod
    def create_agent(self) -> Any:
        pass
    
    @abstractmethod
    def process_message(self,
                        message: str,
                        thread: str,
                        user_id: str) -> str:
        pass
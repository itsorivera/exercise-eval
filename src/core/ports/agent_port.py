from abc import ABC, abstractmethod
from typing import Any

from src.core.models.analysis import AnalysisQueryRequest, AnalysisQueryResponse

class AgentPort(ABC):
    @abstractmethod
    async def create_agent(self) -> Any:
        pass
    
    @abstractmethod
    async def process_message(self,
                        request: AnalysisQueryRequest) -> AnalysisQueryResponse:
        pass
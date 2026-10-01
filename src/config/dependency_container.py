from functools import lru_cache
from typing import Optional
from src.core.ports.llm_provider_port import LLMProviderPort
from src.adapter.providers.aws_bedrock_provder_adapter import AWSBedrockProviderAdapter
from src.core.ports.stm_port import STMProviderPort
from src.adapter.memory.postgres_stm_adapter import PostgresSTMAdapter
from src.core.ports.agent_port import AgentPort
from src.adapter.agent.langchain_agent_adapter import LangChainAgentAdapter

class DependenciesContainer:
    def __init__(self):
        self.llm_provider: Optional[LLMProviderPort] = None
        self.stm: Optional[STMProviderPort] = None
        self.agent_1: Optional[AgentPort] = None
        self.agent_2: Optional[AgentPort] = None

    def get_llm_provider(self) -> LLMProviderPort:
        if self.llm_provider is None:
            self.llm_provider = AWSBedrockProviderAdapter()
        return self.llm_provider
    
    def get_stm(self) -> STMProviderPort:
        if self.stm is None:
            self.stm = PostgresSTMAdapter()
        return self.stm
    
    async def get_agent_1(self) -> AgentPort:
        llm_provider = self.get_llm_provider()
        stm = self.get_stm()

        if self.agent_1 is None:
            self.agent_1 = LangChainAgentAdapter(
                agent_name="agent-financial-analyst",
                llm_provider=llm_provider,
                system_prompt=
                """Eres un agente que que ayudas con la evaluación de indicadores clave, ratios financieros y tendencias de desempeño.
                Los analistas realizan consultas complejas sobre múltiples periodos financieros y esperan obtener resultados rápidos, precisos y con costos controlados para apoyar la toma de decisiones de inversión.""",
                llm_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
                stm=stm,
            )
            await self.agent_1.create_agent()
        return self.agent_1
    

@lru_cache()
def get_dependencies_container() -> DependenciesContainer:
    return DependenciesContainer()

async def get_agent_1() -> AgentPort:
    dependecies = get_dependencies_container()
    return await dependecies.get_agent_1()
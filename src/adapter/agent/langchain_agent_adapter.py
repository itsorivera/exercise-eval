from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langchain_core.tools import BaseTool
from typing import List
from src.core.ports.agent_port import AgentPort
from src.core.ports.llm_provider_port import LLMProviderPort
from src.core.ports.stm_port import STMProviderPort


class LangChainAgentAdapter(AgentPort):
  def __init__(self,
              agent_name: str,
              llm_provider: LLMProviderPort,
              llm_id: str,
              stm_provider: STMProviderPort,
              system_prompt: str = None,
              tools: List[BaseTool] = None):

    self.agent_name = agent_name
    self.llm_provider = llm_provider
    self.llm_id = llm_id
    self.stm_provider = stm_provider
    self.system_prompt = system_prompt
    self.tools = tools
    self.agent_graph_compiled = None
    self.llm = None

  async def create_agent(self,):
    self.llm = self.llm_provider.get_llm(self.llm_id)
    self.llm = self.llm.bind_tools(self.tools) if self.tools else self.llm
    checkpointer = await self.stm_provider.get_state_manager()
    workflow = StateGraph(MessagesState)

    async def call_model(state: MessagesState):
        messages = state["messages"]
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=self.system_prompt)] + messages
        response = await self.llm.ainvoke(messages)
        return {"messages": [response]}

    workflow.add_node("agent", call_model)
    workflow.add_edge(START, "agent")
    workflow.add_edge("agent", END)

    self.agent_graph_compiled = workflow.compile(checkpointer=checkpointer)
    return self.agent_graph_compiled

  async def process_message(self,
                        message,
                        user_id: str,
                        thread_id: str,):
    config = {
        "configurable" : {
            "user_id": user_id,
            "thread_id": thread_id
            }
    }

    result = await self.agent_graph_compiled.ainvoke(
            {"messages": [HumanMessage(content=message)]}, 
            config
        )

    if result and "messages" in result and len(result["messages"]) > 0:
      last_message = result["messages"][-1]
      return {"response": last_message.content}
        
    return {"response": "No response generated"}

    
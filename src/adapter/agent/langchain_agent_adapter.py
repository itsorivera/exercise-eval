from contextlib import aclosing
import asyncio
from typing import Any, List, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langchain_core.tools import BaseTool
from src.core.budget.budget_tracker import (
    MAX_STEPS,
    MAX_TOKENS_BUDGET,
    STOP_REASON_ERROR,
    STOP_REASON_TIMEOUT,
    TIMEOUT_GLOBAL_SECONDS,
    BudgetTracker,
)
from src.core.models.analysis import AnalysisQueryRequest, AnalysisQueryResponse
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
              tools: List[BaseTool] = None,
              max_steps: int = MAX_STEPS,
              max_tokens_budget: int = MAX_TOKENS_BUDGET,
              timeout_global: float = TIMEOUT_GLOBAL_SECONDS):

    self.agent_name = agent_name
    self.llm_provider = llm_provider
    self.llm_id = llm_id
    self.stm_provider = stm_provider
    self.system_prompt = system_prompt
    self.tools = tools
    self.max_steps = max_steps
    self.max_tokens_budget = max_tokens_budget
    self.timeout_global = timeout_global
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

    def should_continue(state: MessagesState):
        last_message = state["messages"][-1]
        return "tools" if getattr(last_message, "tool_calls", None) else END

    workflow.add_node("agent", call_model)
    workflow.add_edge(START, "agent")

    if self.tools:
        workflow.add_node("tools", ToolNode(self.tools))
        workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
        workflow.add_edge("tools", "agent")
    else:
        workflow.add_edge("agent", END)

    self.agent_graph_compiled = workflow.compile(checkpointer=checkpointer)
    return self.agent_graph_compiled

  async def process_message(self,
                        request: AnalysisQueryRequest) -> AnalysisQueryResponse:
    if self.agent_graph_compiled is None:
        await self.create_agent()

    tracker = BudgetTracker(
        max_budget_usd=request.max_budget_usd,
        max_steps=self.max_steps,
        max_tokens_budget=self.max_tokens_budget,
        timeout_global=self.timeout_global,
    )

    config = {
        "configurable": {
            "thread_id": f"{request.analyst_id}:{request.session_id}",
            "analyst_id": request.analyst_id,
            "session_id": request.session_id,
            }
    }

    answer: Optional[str] = None

    try:
        async with asyncio.timeout(self.timeout_global):
            stream = self.agent_graph_compiled.astream(
                    {"messages": [HumanMessage(content=request.query)]},
                    config,
                    stream_mode="updates",
                )

            async with aclosing(stream):
                async for chunk in stream:
                    node, update = self._normalize_chunk(chunk)
                    messages = (update or {}).get("messages") or []
                    if node != "agent" or not messages:
                        continue

                    message = messages[-1]
                    input_tokens, output_tokens = self._extract_usage(message)
                    tracker.register_step(
                        tool_called=self._first_tool_call(message),
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                    )

                    stop_reason = tracker.limit_reached()
                    if stop_reason:
                        tracker.mark_stopped(stop_reason)
                        break

                    if not getattr(message, "tool_calls", None):
                        answer = self._as_text(message.content) or answer

    except TimeoutError:
        tracker.mark_stopped(STOP_REASON_TIMEOUT)
    except asyncio.CancelledError:
        raise
    except Exception:
        tracker.mark_stopped(STOP_REASON_ERROR)
        raise

    return AnalysisQueryResponse(
        analyst_id=request.analyst_id,
        session_id=request.session_id,
        answer=answer or self._partial_answer(tracker),
        completed=tracker.completed,
        steps=tracker.steps,
        steps_used=len(tracker.steps),
        total_tokens=tracker.total_tokens,
        total_cost_usd=tracker.total_cost_usd,
        elapsed_time=tracker.elapsed_time,
        stop_reason=tracker.stop_reason,
        warnings=tracker.warnings,
    )

  def _normalize_chunk(self, chunk: Any) -> Tuple[str, Any]:
    if isinstance(chunk, tuple):
        return chunk[0], chunk[1]
    if isinstance(chunk, dict) and chunk:
        node, update = next(iter(chunk.items()))
        return node, update
    return "", {}

  def _extract_usage(self, message: Any) -> Tuple[int, int]:
    usage = getattr(message, "usage_metadata", None) or {}
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)

    if not input_tokens and not output_tokens:
        raw = (getattr(message, "response_metadata", None) or {}).get("usage") or {}
        input_tokens = int(raw.get("inputTokens") or raw.get("input_tokens") or 0)
        output_tokens = int(raw.get("outputTokens") or raw.get("output_tokens") or 0)

    return input_tokens, output_tokens

  def _first_tool_call(self, message: Any) -> Optional[str]:
    tool_calls = getattr(message, "tool_calls", None) or []
    if not tool_calls:
        return None
    name = tool_calls[0].get("name")
    return name if isinstance(name, str) and name else "unknown"

  def _as_text(self, content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        ]
        return "".join(part for part in parts if part)
    return "" if content is None else str(content)

  def _partial_answer(self, tracker: BudgetTracker) -> str:
    reason = tracker.stop_reason or STOP_REASON_ERROR
    return (
      "Respuesta parcial: el análisis se detuvo antes de completarse "
      f"(motivo: {reason}, pasos ejecutados: {len(tracker.steps)})."
    )
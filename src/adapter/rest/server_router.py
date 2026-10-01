from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from src.core.ports.agent_port import AgentPort
from src.config.dependency_container import get_agent_1

router = APIRouter(prefix="/api/v1/agent-fleet",
                   tags=["agent-fleet"])

@router.post(
    path="/financial-analyst/query",
    description="Endpoint para consultar al asistente financiero.")
async def query_agent1(
    request: dict,
    agent: Annotated[AgentPort, Depends(get_agent_1)]
    ):
    try:
        response = await agent.process_message(
            message=request["question"],
            thread="default-thread",
            user_id="default-user"
        )
        return {
            "response": response["response"]
        }
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=str(e))
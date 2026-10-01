from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from src.core.models.analysis import AnalysisQueryRequest, AnalysisQueryResponse
from src.core.ports.agent_port import AgentPort
from src.config.dependency_container import get_agent_1

router = APIRouter(prefix="/api/v1/analysis",
                   tags=["analysis"])

@router.post(
    path="/query",
    description="Endpoint para consultar al asistente financiero bajo límites de pasos, tokens, costo y tiempo.",
    response_model=AnalysisQueryResponse)
async def query_analysis(
    request: AnalysisQueryRequest,
    agent: Annotated[AgentPort, Depends(get_agent_1)]
    ):
    try:
        return await agent.process_message(request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=str(e))
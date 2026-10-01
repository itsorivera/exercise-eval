from typing import List, Optional

from pydantic import BaseModel, Field


class StepMetric(BaseModel):
    """Métricas de un paso individual del agente."""

    step_number: int = Field(..., description="Número de paso, empezando en 1.")
    tool_called: Optional[str] = Field(
        default=None,
        description="Nombre de la herramienta invocada en el paso, o null si el modelo no pidió herramientas.",
    )
    tokens_used: int = Field(..., ge=0, description="Tokens consumidos en el paso (input + output).")
    cumulative_cost: float = Field(..., ge=0, description="Costo acumulado en USD hasta el paso.")
    elapsed_time: float = Field(..., ge=0, description="Segundos transcurridos desde el inicio de la ejecución.")


class AnalysisQueryRequest(BaseModel):
    analyst_id: str = Field(..., min_length=1, examples=["A01"])
    session_id: str = Field(..., min_length=1, examples=["S001"])
    query: str = Field(..., min_length=1, examples=["¿Cómo evolucionó el margen neto en los últimos 5 meses?"])
    max_budget_usd: float = Field(
        default=0.50,
        gt=0,
        examples=[0.50],
        description="Presupuesto máximo de gasto en USD para la ejecución.",
    )


class AnalysisQueryResponse(BaseModel):
    analyst_id: str
    session_id: str
    answer: str = Field(..., description="Respuesta final o respuesta parcial si se agotó un límite.")
    completed: bool = Field(..., description="True si el agente terminó sin agotar ningún límite.")
    steps: List[StepMetric] = Field(default_factory=list)
    steps_used: int = Field(..., ge=0)
    total_tokens: int = Field(..., ge=0)
    total_cost_usd: float = Field(..., ge=0)
    elapsed_time: float = Field(..., ge=0)
    stop_reason: Optional[str] = Field(
        default=None,
        description="Límite que se agotó: budget, tokens, max_steps, timeout o error.",
    )
    warnings: List[str] = Field(default_factory=list)
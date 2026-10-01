import json
import os
import time
from typing import Any, List, Optional

from src.core.models.analysis import BudgetStatus, StepMetric

MAX_STEPS = 8
MAX_TOKENS_BUDGET = 10000
TIMEOUT_GLOBAL_SECONDS = 45.0
MAX_IDENTICAL_TOOL_CALLS = 2

DEFAULT_INPUT_COST_PER_MTOK = 3.0
DEFAULT_OUTPUT_COST_PER_MTOK = 15.0

TOKENS_PER_MTOK = 1_000_000

STOP_REASON_BUDGET = "budget"
STOP_REASON_TOKENS = "tokens"
STOP_REASON_MAX_STEPS = "max_steps"
STOP_REASON_TIMEOUT = "timeout"
STOP_REASON_LOOP = "loop_detected"
STOP_REASON_ERROR = "error"


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


class BudgetTracker:
    """Controla pasos, tokens, costo y tiempo de una ejecución, y registra sus métricas."""

    def __init__(self,
                 max_budget_usd: float,
                 max_steps: int = MAX_STEPS,
                 max_tokens_budget: int = MAX_TOKENS_BUDGET,
                 timeout_global: float = TIMEOUT_GLOBAL_SECONDS,
                 max_identical_tool_calls: int = MAX_IDENTICAL_TOOL_CALLS):
        self.max_budget_usd = max_budget_usd
        self.max_steps = max_steps
        self.max_tokens_budget = max_tokens_budget
        self.timeout_global = timeout_global
        self.max_identical_tool_calls = max_identical_tool_calls
        self.input_cost_per_mtok = _env_float(
            "BEDROCK_INPUT_COST_PER_MTOK", DEFAULT_INPUT_COST_PER_MTOK)
        self.output_cost_per_mtok = _env_float(
            "BEDROCK_OUTPUT_COST_PER_MTOK", DEFAULT_OUTPUT_COST_PER_MTOK)

        self.steps: List[StepMetric] = []
        self.total_tokens = 0
        self.total_cost_usd = 0.0
        self.stop_reason: Optional[str] = None
        self.looping_tool: Optional[str] = None
        self._tool_call_counts: dict = {}
        self._started_at = time.perf_counter()

    @property
    def elapsed_time(self) -> float:
        return round(time.perf_counter() - self._started_at, 4)

    @property
    def remaining_time(self) -> float:
        return round(max(0.0, self.timeout_global - self.elapsed_time), 4)

    @property
    def remaining_budget_usd(self) -> float:
        return round(max(0.0, self.max_budget_usd - self.total_cost_usd), 6)

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.max_tokens_budget - self.total_tokens)

    @property
    def remaining_steps(self) -> int:
        return max(0, self.max_steps - len(self.steps))

    def status(self) -> BudgetStatus:
        return BudgetStatus(
            max_budget_usd=self.max_budget_usd,
            max_steps=self.max_steps,
            max_tokens_budget=self.max_tokens_budget,
            timeout_global_seconds=self.timeout_global,
            spent_usd=self.total_cost_usd,
            remaining_usd=self.remaining_budget_usd,
            steps_used=len(self.steps),
            remaining_steps=self.remaining_steps,
            tokens_used=self.total_tokens,
            remaining_tokens=self.remaining_tokens,
            elapsed_time=self.elapsed_time,
            remaining_time=self.remaining_time,
        )

    def cost_of(self, input_tokens: int, output_tokens: int) -> float:
        return round(
            (input_tokens * self.input_cost_per_mtok + output_tokens * self.output_cost_per_mtok) / TOKENS_PER_MTOK,
            6,
        )

    def register_step(self,
                     tool_called: Optional[str],
                     input_tokens: int,
                     output_tokens: int,
                     tool_args: Optional[dict] = None) -> StepMetric:
        tokens_used = max(0, input_tokens) + max(0, output_tokens)
        self.total_tokens += tokens_used
        self.total_cost_usd = round(self.total_cost_usd + self.cost_of(input_tokens, output_tokens), 6)
        self._count_tool_call(tool_called, tool_args)

        metric = StepMetric(
            step_number=len(self.steps) + 1,
            tool_called=tool_called,
            tokens_used=tokens_used,
            cumulative_cost=self.total_cost_usd,
            elapsed_time=self.elapsed_time,
        )
        self.steps.append(metric)
        return metric

    def _count_tool_call(self,
                         tool_called: Optional[str],
                         tool_args: Optional[dict]) -> None:
        if not tool_called:
            return
        signature = f"{tool_called}:{json.dumps(tool_args or {}, sort_keys=True, default=str)}"
        self._tool_call_counts[signature] = self._tool_call_counts.get(signature, 0) + 1

    @property
    def is_looping(self) -> bool:
        return self._looping_signature() is not None

    def _looping_signature(self) -> Optional[str]:
        for signature, count in self._tool_call_counts.items():
            if count >= self.max_identical_tool_calls:
                return signature
        return None

    @property
    def is_budget_exceeded(self) -> bool:
        return self.total_cost_usd >= self.max_budget_usd

    @property
    def is_tokens_exceeded(self) -> bool:
        return self.total_tokens >= self.max_tokens_budget

    @property
    def is_steps_exceeded(self) -> bool:
        return len(self.steps) >= self.max_steps

    @property
    def is_timeout_exceeded(self) -> bool:
        return self.elapsed_time >= self.timeout_global

    def limit_reached(self) -> Optional[str]:
        if self.is_looping:
            self.looping_tool = self._looping_signature().split(":", 1)[0]
            return STOP_REASON_LOOP
        if self.is_budget_exceeded:
            return STOP_REASON_BUDGET
        if self.is_tokens_exceeded:
            return STOP_REASON_TOKENS
        if self.is_steps_exceeded:
            return STOP_REASON_MAX_STEPS
        if self.is_timeout_exceeded:
            return STOP_REASON_TIMEOUT
        return None

    def mark_stopped(self, reason: str) -> None:
        self.stop_reason = reason

    @property
    def completed(self) -> bool:
        return self.stop_reason is None

    @property
    def warnings(self) -> List[str]:
        if self.stop_reason is None:
            return []
        if self.stop_reason == STOP_REASON_BUDGET:
            return [
                f"Respuesta parcial: se agotó el presupuesto de "
                f"{self.max_budget_usd:.4f} USD (consumido {self.total_cost_usd:.4f} USD)."
            ]
        if self.stop_reason == STOP_REASON_TOKENS:
            return [
                f"Respuesta parcial: se agotó el presupuesto de tokens de "
                f"{self.max_tokens_budget} (consumidos {self.total_tokens})."
            ]
        if self.stop_reason == STOP_REASON_MAX_STEPS:
            return [
                f"Respuesta parcial: se alcanzó el máximo de {self.max_steps} pasos sin "
                "completar el análisis."
            ]
        if self.stop_reason == STOP_REASON_TIMEOUT:
            return [
                f"Respuesta parcial: se agotó el tiempo global de {self.timeout_global:.0f}s "
                f"(transcurrido {self.elapsed_time:.2f}s)."
            ]
        if self.stop_reason == STOP_REASON_LOOP:
            return [
                f"Respuesta parcial: se detectó un bucle, la herramienta "
                f"'{self.looping_tool}' se invocó {self.max_identical_tool_calls} veces con los "
                "mismos argumentos."
            ]
        return ["Respuesta parcial: la ejecución terminó con un error inesperado."]
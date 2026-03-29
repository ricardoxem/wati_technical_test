from pydantic import BaseModel

from wati_agent.domain.models import ExecutionPlan
from wati_agent.llm.base import BaseLLMProvider


class PlanningRequest(BaseModel):
    """Small wrapper for the user's raw instruction."""

    user_input: str


class Planner:
    """Turns a natural-language request into a structured plan."""

    def __init__(self, llm_provider: BaseLLMProvider) -> None:
        self.llm_provider = llm_provider

    def build_plan(self, request: PlanningRequest) -> ExecutionPlan:
        return self.llm_provider.generate_plan(request.user_input)

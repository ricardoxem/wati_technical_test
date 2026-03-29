from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PlanStatus(str, Enum):
    """High-level state of a generated plan."""

    READY = "ready"
    NEEDS_CLARIFICATION = "needs_clarification"
    UNSUPPORTED = "unsupported"


class PlanStep(BaseModel):
    """One human-readable action that the executor can carry out."""

    id: str
    domain: str
    action: str
    description: str
    endpoint_hint: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class ExecutionPlan(BaseModel):
    """Structured output produced by the planner before execution starts."""

    user_request: str
    summary: str
    status: PlanStatus = PlanStatus.READY
    requires_confirmation: bool = True
    missing_information: list[str] = Field(default_factory=list)
    steps: list[PlanStep] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    """Final result returned after the executor finishes running the plan."""

    success: bool
    summary: str
    completed_steps: list[str] = Field(default_factory=list)
    failed_steps: list[str] = Field(default_factory=list)
    details: list[str] = Field(default_factory=list)

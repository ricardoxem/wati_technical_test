from wati_agent.agent.executor import PlanExecutor
from wati_agent.agent.memory import SessionMemory
from wati_agent.agent.planner import Planner, PlanningRequest
from wati_agent.agent.validator import PlanValidator
from wati_agent.domain.models import ExecutionPlan, ExecutionResult


class AgentResponse:
    """Groups the plan preview and, when available, the execution result."""

    def __init__(self, plan: ExecutionPlan, result: ExecutionResult | None = None) -> None:
        self.plan = plan
        self.result = result


class AgentOrchestrator:
    """Coordinates planning, validation, memory, and execution."""

    def __init__(
        self,
        planner: Planner,
        validator: PlanValidator,
        executor: PlanExecutor,
        memory: SessionMemory | None = None,
    ) -> None:
        self.planner = planner
        self.validator = validator
        self.executor = executor
        self.memory = memory or SessionMemory()

    def preview(self, user_input: str) -> AgentResponse:
        self.memory.remember(user_input)
        draft_plan = self.planner.build_plan(PlanningRequest(user_input=user_input))
        checked_plan = self.validator.validate(draft_plan)
        return AgentResponse(plan=checked_plan)

    def execute(self, plan: ExecutionPlan) -> AgentResponse:
        result = self.executor.execute(plan)
        return AgentResponse(plan=plan, result=result)

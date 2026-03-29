from abc import ABC, abstractmethod

from wati_agent.domain.models import ExecutionPlan


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate_plan(self, user_input: str) -> ExecutionPlan:
        raise NotImplementedError

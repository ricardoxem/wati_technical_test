from wati_agent.domain.models import PlanStep
from wati_agent.integrations.wati.base_client import BaseWatiClient


class RealWatiClient(BaseWatiClient):
    def __init__(self, base_url: str, api_token: str) -> None:
        self.base_url = base_url
        self.api_token = api_token

    def execute_step(self, step: PlanStep) -> None:
        raise NotImplementedError("Real WATI API integration will be implemented later.")

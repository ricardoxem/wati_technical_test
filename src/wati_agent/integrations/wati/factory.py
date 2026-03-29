from wati_agent.app.config import Settings
from wati_agent.integrations.wati.base_client import BaseWatiClient
from wati_agent.integrations.wati.mock_client import MockWatiClient
from wati_agent.integrations.wati.real_client import RealWatiClient


def build_wati_client(settings: Settings) -> BaseWatiClient:
    if settings.wati_backend.lower() == "real":
        return RealWatiClient(base_url=settings.wati_base_url, api_token=settings.wati_api_token)

    return MockWatiClient(base_url=settings.wati_base_url, api_token=settings.wati_api_token)

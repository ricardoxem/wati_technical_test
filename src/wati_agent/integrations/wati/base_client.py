from abc import ABC, abstractmethod
from typing import Any

from wati_agent.domain.models import PlanStep


class BaseWatiClient(ABC):
    """Shared contract for any WATI client implementation."""

    @abstractmethod
    def get_contacts(self, *, tag: str | None = None, city: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_templates(self, *, template_name: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_operators(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def send_template_message(
        self,
        *,
        whatsapp_number: str,
        template_name: str,
        broadcast_name: str = "",
        parameters: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def assign_ticket_to_team(self, *, whatsapp_number: str, team_name: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def add_tag_to_contact(self, *, whatsapp_number: str, tag: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def send_broadcast_to_segment(
        self,
        *,
        template_name: str,
        broadcast_name: str,
        segment_name: str,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def execute_step(self, step: PlanStep) -> dict[str, Any]:
        raise NotImplementedError

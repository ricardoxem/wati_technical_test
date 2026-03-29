from typing import Any

import httpx

from wati_agent.domain.models import PlanStep
from wati_agent.integrations.wati.base_client import BaseWatiClient


class MockWatiClient(BaseWatiClient):
    """HTTP client for the local FastAPI-based mock WATI API."""

    def __init__(self, base_url: str, api_token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout = 30.0

    def get_contacts(self, *, tag: str | None = None, city: str | None = None) -> dict[str, Any]:
        query_params: dict[str, str] = {}
        if tag:
            query_params["tag"] = tag
        if city:
            query_params["city"] = city

        return self._request("GET", "/api/v1/getContacts", params=query_params)

    def get_templates(self, *, template_name: str | None = None) -> dict[str, Any]:
        query_params: dict[str, str] = {}
        if template_name:
            query_params["templateName"] = template_name

        return self._request("GET", "/api/v1/getMessageTemplates", params=query_params)

    def get_operators(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/getOperators")

    def send_template_message(
        self,
        *,
        whatsapp_number: str,
        template_name: str,
        broadcast_name: str = "",
        parameters: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/api/v1/sendTemplateMessage/{whatsapp_number}",
            json={
                "template_name": template_name,
                "broadcast_name": broadcast_name,
                "parameters": parameters or [],
            },
        )

    def assign_ticket_to_team(self, *, whatsapp_number: str, team_name: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/tickets/assign",
            json={
                "whatsapp_number": whatsapp_number,
                "team_name": team_name,
            },
        )

    def add_tag_to_contact(self, *, whatsapp_number: str, tag: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/api/v1/addTag/{whatsapp_number}",
            json={"tag": tag},
        )

    def send_broadcast_to_segment(
        self,
        *,
        template_name: str,
        broadcast_name: str,
        segment_name: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/sendBroadcastToSegment",
            json={
                "template_name": template_name,
                "broadcast_name": broadcast_name,
                "segment_name": segment_name,
            },
        )

    def execute_step(self, step: PlanStep) -> dict[str, Any]:
        if step.action == "get_contacts_by_tag":
            return self.get_contacts(
                tag=self._read_text_param(step, "tag"),
                city=self._read_optional_text_param(step, "city"),
            )

        if step.action == "get_template_by_name":
            return self.get_templates(template_name=self._read_text_param(step, "template_name"))

        if step.action == "send_template_message":
            return self.send_template_message(
                whatsapp_number=self._read_text_param(step, "whatsapp_number"),
                template_name=self._read_text_param(step, "template_name"),
                broadcast_name=self._read_text_param(step, "broadcast_name", default=""),
                parameters=self._read_list_param(step, "parameters"),
            )

        if step.action == "assign_ticket_to_team":
            return self.assign_ticket_to_team(
                whatsapp_number=self._read_text_param(step, "whatsapp_number"),
                team_name=self._read_text_param(step, "team_name"),
            )

        if step.action == "add_tag_to_contact":
            return self.add_tag_to_contact(
                whatsapp_number=self._read_text_param(step, "whatsapp_number"),
                tag=self._read_text_param(step, "tag"),
            )

        if step.action == "send_broadcast_to_segment":
            return self.send_broadcast_to_segment(
                template_name=self._read_text_param(step, "template_name"),
                broadcast_name=self._read_text_param(step, "broadcast_name", default=""),
                segment_name=self._read_text_param(step, "segment_name"),
            )

        raise ValueError(f"Unsupported mock step action: {step.action}")

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = httpx.request(
            method=method,
            url=f"{self.base_url}{path}",
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            },
            params=params,
            json=json,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def _read_text_param(self, step: PlanStep, param_name: str, default: str | None = None) -> str:
        param_value = step.params.get(param_name, default)
        if param_value is None:
            raise ValueError(f"Step {step.id} is missing parameter '{param_name}'.")
        return str(param_value)

    def _read_optional_text_param(self, step: PlanStep, param_name: str) -> str | None:
        param_value = step.params.get(param_name)
        if param_value is None:
            return None

        clean_value = str(param_value).strip()
        return clean_value or None

    def _read_list_param(
        self,
        step: PlanStep,
        param_name: str,
        default: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        param_value = step.params.get(param_name, default or [])
        if isinstance(param_value, list):
            return [item for item in param_value if isinstance(item, dict)]
        return default or []

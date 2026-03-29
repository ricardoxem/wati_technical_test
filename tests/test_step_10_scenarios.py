from typing import Any

from wati_agent.agent.executor import PlanExecutor
from wati_agent.agent.validator import PlanValidator
from wati_agent.domain.models import ExecutionPlan, PlanStatus, PlanStep
from wati_agent.integrations.wati.base_client import BaseWatiClient


class FakeWatiClient(BaseWatiClient):
    """Small fake client used to test execution flows without HTTP."""

    def __init__(self, *, fail_for_numbers: set[str] | None = None) -> None:
        self.fail_for_numbers = fail_for_numbers or set()
        self.sent_to: list[str] = []

    def get_contacts(self, *, tag: str | None = None, city: str | None = None) -> dict[str, Any]:
        contacts = [
            {
                "whatsapp_number": "6281234567890",
                "name": "Alya",
                "tags": ["VIP"],
                "attributes": {"city": "Jakarta"},
            },
            {
                "whatsapp_number": "6281234567892",
                "name": "Citra",
                "tags": ["VIP", "Renewal"],
                "attributes": {"city": "Jakarta"},
            },
        ]
        return {
            "total": len(contacts),
            "contacts": contacts,
        }

    def get_templates(self, *, template_name: str | None = None) -> dict[str, Any]:
        return {
            "total": 1,
            "templates": [
                {
                    "name": template_name or "renewal_reminder",
                    "category": "utility",
                    "parameters": ["body_1"],
                }
            ],
        }

    def get_operators(self) -> dict[str, Any]:
        return {
            "operators": [
                {"email": "support@company.com", "team_name": "Support"},
            ]
        }

    def send_template_message(
        self,
        *,
        whatsapp_number: str,
        template_name: str,
        broadcast_name: str = "",
        parameters: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        if whatsapp_number in self.fail_for_numbers:
            raise ValueError(f"Mock send failure for {whatsapp_number}")

        self.sent_to.append(whatsapp_number)
        return {
            "whatsappNumber": whatsapp_number,
            "template_name": template_name,
            "status": "accepted",
        }

    def assign_ticket_to_team(self, *, whatsapp_number: str, team_name: str) -> dict[str, Any]:
        return {
            "whatsappNumber": whatsapp_number,
            "teamName": team_name,
            "assignedTo": "support@company.com",
            "status": "assigned",
        }

    def add_tag_to_contact(self, *, whatsapp_number: str, tag: str) -> dict[str, Any]:
        return {
            "whatsappNumber": whatsapp_number,
            "tags": [tag],
            "status": "updated",
        }

    def send_broadcast_to_segment(
        self,
        *,
        template_name: str,
        broadcast_name: str,
        segment_name: str,
    ) -> dict[str, Any]:
        return {
            "template_name": template_name,
            "broadcast_name": broadcast_name,
            "segmentName": segment_name,
            "audienceSize": 3,
            "status": "queued",
        }

    def execute_step(self, step: PlanStep) -> dict[str, Any]:
        if step.action == "get_contacts_by_tag":
            return self.get_contacts(tag=step.params.get("tag"))

        if step.action == "get_template_by_name":
            return self.get_templates(template_name=step.params.get("template_name"))

        if step.action == "assign_ticket_to_team":
            return self.assign_ticket_to_team(
                whatsapp_number=str(step.params["whatsapp_number"]),
                team_name=str(step.params["team_name"]),
            )

        if step.action == "add_tag_to_contact":
            return self.add_tag_to_contact(
                whatsapp_number=str(step.params["whatsapp_number"]),
                tag=str(step.params["tag"]),
            )

        if step.action == "send_broadcast_to_segment":
            return self.send_broadcast_to_segment(
                template_name=str(step.params["template_name"]),
                broadcast_name=str(step.params.get("broadcast_name", "")),
                segment_name=str(step.params["segment_name"]),
            )

        raise ValueError(f"Unsupported fake action {step.action}")


def test_happy_path_executes_template_flow_successfully() -> None:
    fake_client = FakeWatiClient()
    executor = PlanExecutor(wati_client=fake_client)

    plan = ExecutionPlan(
        user_request="Send the renewal_reminder template to all VIP contacts",
        summary="Find VIP contacts, validate template, and send the template.",
        steps=[
            PlanStep(
                id="step-1",
                domain="contacts",
                action="get_contacts_by_tag",
                description="Find VIP contacts.",
                params={"tag": "VIP"},
            ),
            PlanStep(
                id="step-2",
                domain="templates",
                action="get_template_by_name",
                description="Check the template.",
                params={"template_name": "renewal_reminder"},
            ),
            PlanStep(
                id="step-3",
                domain="messages",
                action="send_template_message",
                description="Send the template.",
                params={"template_name": "renewal_reminder"},
            ),
        ],
    )

    result = executor.execute(plan)

    assert result.success is True
    assert result.failed_steps == []
    assert result.completed_steps == ["step-1", "step-2", "step-3"]
    assert "Sent the requested template to 2 contact(s)." == result.summary
    assert fake_client.sent_to == ["6281234567890", "6281234567892"]


def test_validator_marks_missing_parameters_for_clarification() -> None:
    validator = PlanValidator()
    plan = ExecutionPlan(
        user_request="Escalate this contact",
        summary="Assign the contact to a team.",
        steps=[
            PlanStep(
                id="step-1",
                domain="operators_tickets",
                action="assign_ticket_to_team",
                description="Assign the conversation.",
                params={},
            )
        ],
    )

    checked_plan = validator.validate(plan)

    assert checked_plan.status == PlanStatus.NEEDS_CLARIFICATION
    assert "Step step-1 is missing required parameter 'whatsapp number'." in checked_plan.missing_information
    assert "Step step-1 is missing required parameter 'team name'." in checked_plan.missing_information
    assert checked_plan.requires_confirmation is True


def test_executor_reports_partial_failure_when_one_contact_send_fails() -> None:
    fake_client = FakeWatiClient(fail_for_numbers={"6281234567892"})
    executor = PlanExecutor(wati_client=fake_client)

    plan = ExecutionPlan(
        user_request="Send the renewal_reminder template to all VIP contacts",
        summary="Find VIP contacts, validate template, and send the template.",
        steps=[
            PlanStep(
                id="step-1",
                domain="contacts",
                action="get_contacts_by_tag",
                description="Find VIP contacts.",
                params={"tag": "VIP"},
            ),
            PlanStep(
                id="step-2",
                domain="messages",
                action="send_template_message",
                description="Send the template.",
                params={"template_name": "renewal_reminder"},
            ),
        ],
    )

    result = executor.execute(plan)

    assert result.success is False
    assert result.completed_steps == ["step-1"]
    assert result.failed_steps == ["step-2"]
    assert result.summary == "Sent the requested template to 1 contact(s), but 1 contact(s) failed."
    assert "Step step-2 completed with partial failures." in result.details


def test_validator_extracts_team_name_from_step_description() -> None:
    validator = PlanValidator()
    plan = ExecutionPlan(
        user_request="Escalate 6281234567890 to the Support team and add the escalated tag",
        summary="Escalate contact to Support team and add escalated tag",
        steps=[
            PlanStep(
                id="step-1",
                domain="operators_tickets",
                action="assign_ticket_to_team",
                description="Assign contact 6281234567890 to Support team",
                params={},
            ),
            PlanStep(
                id="step-2",
                domain="tags",
                action="add_tag_to_contact",
                description="Add tag escalated to contact 6281234567890",
                params={},
            ),
        ],
    )

    checked_plan = validator.validate(plan)

    assert checked_plan.status == PlanStatus.READY
    assert checked_plan.steps[0].params["team_name"] == "Support"
    assert checked_plan.steps[0].params["whatsapp_number"] == "6281234567890"
    assert checked_plan.steps[1].params["tag"] == "escalated"

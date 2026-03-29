from typing import Any

from wati_agent.domain.models import ExecutionPlan, ExecutionResult
from wati_agent.integrations.wati.base_client import BaseWatiClient


class PlanExecutor:
    """Runs each step in order using the selected WATI client."""

    def __init__(self, wati_client: BaseWatiClient) -> None:
        self.wati_client = wati_client

    def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        completed_step_ids: list[str] = []
        failed_step_ids: list[str] = []
        execution_details: list[str] = []
        step_results: dict[str, dict[str, Any]] = {}

        for step in plan.steps:
            try:
                result = self._run_step(step=step, previous_results=step_results)
                step_results[step.id] = result
                execution_details.extend(self._build_detail_lines(step.action, result))
                if self._result_has_partial_failure(result):
                    failed_step_ids.append(step.id)
                    execution_details.append(
                        f"Step {step.id} completed with partial failures."
                    )
                    break

                completed_step_ids.append(step.id)
            except Exception as exc:
                failed_step_ids.append(step.id)
                execution_details.append(f"Step {step.id} failed: {exc}")
                break

        was_successful = len(failed_step_ids) == 0
        summary = self._build_summary(
            plan=plan,
            completed_step_ids=completed_step_ids,
            failed_step_ids=failed_step_ids,
            previous_results=step_results,
        )

        return ExecutionResult(
            success=was_successful,
            summary=summary,
            completed_steps=completed_step_ids,
            failed_steps=failed_step_ids,
            details=execution_details,
        )

    def _run_step(self, step: Any, previous_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
        if step.action == "send_template_message":
            return self._send_template_messages(step=step, previous_results=previous_results)

        return self.wati_client.execute_step(step)

    def _send_template_messages(
        self,
        *,
        step: Any,
        previous_results: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        explicit_number = step.params.get("whatsapp_number")
        if explicit_number:
            sent_message = self.wati_client.send_template_message(
                whatsapp_number=str(explicit_number),
                template_name=str(step.params["template_name"]),
                broadcast_name=str(step.params.get("broadcast_name", "")),
                parameters=self._read_message_parameters(step.params),
            )
            return {
                "sent_messages": [sent_message],
                "total_sent": 1,
            }

        latest_contacts = self._find_latest_contacts(previous_results)
        if not latest_contacts:
            raise ValueError(
                "No target contacts are available for the send_template_message step."
            )

        sent_messages: list[dict[str, Any]] = []
        failed_messages: list[dict[str, str]] = []
        for contact in latest_contacts:
            try:
                message_result = self.wati_client.send_template_message(
                    whatsapp_number=str(contact["whatsapp_number"]),
                    template_name=str(step.params["template_name"]),
                    broadcast_name=str(step.params.get("broadcast_name", "")),
                    parameters=self._build_contact_parameters(contact, step.params),
                )
                sent_messages.append(message_result)
            except Exception as exc:
                failed_messages.append(
                    {
                        "whatsapp_number": str(contact["whatsapp_number"]),
                        "reason": str(exc),
                    }
                )

        return {
            "sent_messages": sent_messages,
            "total_sent": len(sent_messages),
            "failed_messages": failed_messages,
            "total_failed": len(failed_messages),
        }

    def _find_latest_contacts(
        self,
        previous_results: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        for result in reversed(list(previous_results.values())):
            contacts = result.get("contacts")
            if isinstance(contacts, list) and contacts:
                return [contact for contact in contacts if isinstance(contact, dict)]
        return []

    def _read_message_parameters(self, step_params: dict[str, Any]) -> list[dict[str, str]]:
        raw_parameters = step_params.get("parameters", [])
        if isinstance(raw_parameters, list):
            return [item for item in raw_parameters if isinstance(item, dict)]
        return []

    def _build_contact_parameters(
        self,
        contact: dict[str, Any],
        step_params: dict[str, Any],
    ) -> list[dict[str, str]]:
        provided_parameters = self._read_message_parameters(step_params)
        if provided_parameters:
            return provided_parameters

        contact_name = str(contact.get("name", "customer"))
        return [{"name": "body_1", "value": contact_name}]

    def _build_detail_lines(self, action_name: str, result: dict[str, Any]) -> list[str]:
        if action_name == "get_contacts_by_tag":
            total_contacts = result.get("total", 0)
            return [f"Found {total_contacts} matching contact(s)."]

        if action_name == "get_template_by_name":
            templates = result.get("templates", [])
            if templates:
                template_name = templates[0].get("name", "unknown")
                return [f"Template {template_name} is available."]

        if action_name == "send_template_message":
            total_sent = result.get("total_sent", 0)
            detail_lines = [f"Sent template messages to {total_sent} contact(s)."]
            total_failed = result.get("total_failed", 0)
            if total_failed:
                detail_lines.append(f"{total_failed} contact(s) failed during message sending.")
            return detail_lines

        if action_name == "assign_ticket_to_team":
            team_name = result.get("teamName", "unknown")
            return [f"Assigned the conversation to team {team_name}."]

        if action_name == "add_tag_to_contact":
            tags = result.get("tags", [])
            return [f"Updated contact tags: {', '.join(tags)}."]

        if action_name == "send_broadcast_to_segment":
            segment_name = result.get("segmentName", "unknown")
            audience_size = result.get("audienceSize", 0)
            return [f"Queued a broadcast for segment {segment_name} with {audience_size} contact(s)."]

        return [f"Completed action {action_name}."]

    def _build_summary(
        self,
        *,
        plan: ExecutionPlan,
        completed_step_ids: list[str],
        failed_step_ids: list[str],
        previous_results: dict[str, dict[str, Any]],
    ) -> str:
        if failed_step_ids:
            latest_message_result = self._find_result_by_key(previous_results, "total_sent")
            if latest_message_result and latest_message_result.get("total_failed", 0):
                return (
                    f"Sent the requested template to {latest_message_result['total_sent']} contact(s), "
                    f"but {latest_message_result['total_failed']} contact(s) failed."
                )
            return f"Execution stopped after {len(completed_step_ids)} successful step(s)."

        latest_message_result = self._find_result_by_key(previous_results, "total_sent")
        if latest_message_result:
            return f"Sent the requested template to {latest_message_result['total_sent']} contact(s)."

        latest_broadcast_result = self._find_result_by_key(previous_results, "segmentName")
        if latest_broadcast_result and latest_broadcast_result.get("status") == "queued":
            return (
                f"Queued the broadcast {latest_broadcast_result.get('broadcast_name', '')} "
                f"for segment {latest_broadcast_result.get('segmentName', 'unknown')}."
            ).strip()

        latest_ticket_result = self._find_result_by_key(previous_results, "assignedTo")
        if latest_ticket_result:
            return f"Assigned the contact to team {latest_ticket_result.get('teamName', 'unknown')}."

        return f"Executed {len(completed_step_ids)} step(s) for the request: {plan.user_request}"

    def _find_result_by_key(
        self,
        previous_results: dict[str, dict[str, Any]],
        key_name: str,
    ) -> dict[str, Any] | None:
        for result in reversed(list(previous_results.values())):
            if key_name in result:
                return result
        return None

    def _result_has_partial_failure(self, result: dict[str, Any]) -> bool:
        total_failed = result.get("total_failed", 0)
        return isinstance(total_failed, int) and total_failed > 0

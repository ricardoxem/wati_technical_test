import json

import httpx

from wati_agent.domain.models import ExecutionPlan, PlanStatus, PlanStep
from wati_agent.llm.base import BaseLLMProvider

SUPPORTED_ACTIONS = {
    "get_contacts_by_tag": {
        "domain": "contacts",
        "endpoint_hint": "GET /api/v1/getContacts",
    },
    "get_template_by_name": {
        "domain": "templates",
        "endpoint_hint": "GET /api/v1/getMessageTemplates",
    },
    "send_template_message": {
        "domain": "messages",
        "endpoint_hint": "POST /api/v1/sendTemplateMessage/{whatsappNumber}",
    },
    "assign_ticket_to_team": {
        "domain": "operators_tickets",
        "endpoint_hint": "POST /api/v1/tickets/assign",
    },
    "add_tag_to_contact": {
        "domain": "tags",
        "endpoint_hint": "POST /api/v1/addTag/{whatsappNumber}",
    },
    "send_broadcast_to_segment": {
        "domain": "broadcasts",
        "endpoint_hint": "POST /api/v1/sendBroadcastToSegment",
    },
}


class OllamaProvider(BaseLLMProvider):
    """Uses the local Ollama HTTP API to generate structured plans."""

    def __init__(self, model: str, host: str, timeout_seconds: float = 300.0) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def generate_plan(self, user_input: str) -> ExecutionPlan:
        prompt = self._build_prompt(user_input)

        try:
            response = httpx.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.1,
                    },
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            response_text = response.json().get("response", "{}")
            plan_payload = self._load_json(response_text)
            return self._payload_to_plan(user_input, plan_payload)
        except Exception as exc:
            return ExecutionPlan(
                user_request=user_input,
                summary="The local Ollama provider could not generate a valid plan.",
                status=PlanStatus.NEEDS_CLARIFICATION,
                missing_information=[f"Ollama request failed: {exc}"],
                steps=[],
            )

    def _build_prompt(self, user_input: str) -> str:
        return f"""
You are an orchestration planner for a WATI WhatsApp automation agent.

Your job is to convert a user request into a strict JSON object for a very small MVP.
Do not explain anything. Return JSON only.

Supported actions for this MVP:

1. get_contacts_by_tag
   domain: contacts
   endpoint_hint: GET /api/v1/getContacts
   use when the request mentions contacts with a specific tag

2. get_template_by_name
   domain: templates
   endpoint_hint: GET /api/v1/getMessageTemplates
   use when the request mentions checking or using a template

3. send_template_message
   domain: messages
   endpoint_hint: POST /api/v1/sendTemplateMessage/{{whatsappNumber}}
   use when the request asks to send a template to one or more contacts

4. assign_ticket_to_team
   domain: operators_tickets
   endpoint_hint: POST /api/v1/tickets/assign
   use when the request asks to escalate or assign a contact to a team

5. add_tag_to_contact
   domain: tags
   endpoint_hint: POST /api/v1/addTag/{{whatsappNumber}}
   use when the request asks to add a tag to a contact

6. send_broadcast_to_segment
   domain: broadcasts
   endpoint_hint: POST /api/v1/sendBroadcastToSegment
   use when the request asks to send a broadcast to a filtered audience

Rules:
- Return valid JSON only. No markdown. No prose. No code fences.
- Prefer plans with 1 to 4 steps.
- Only use the supported actions listed above.
- Do not invent new actions, domains, or endpoint hints.
- Use requires_confirmation=true for sends, broadcasts, or assignments.
- If the request is ambiguous or missing information, keep steps empty and explain what is missing.
- Keep summaries short, concrete, and human-readable.
- Each step must have: id, domain, action, description, endpoint_hint, params.

Return JSON with this schema:
{{
  "summary": "string",
  "requires_confirmation": true,
  "missing_information": ["string"],
  "steps": []
}}

Or:

{{
  "summary": "string",
  "requires_confirmation": true,
  "missing_information": ["string"],
  "steps": [
    {{
      "id": "step-1",
      "domain": "contacts",
      "action": "get_contacts_by_tag",
      "description": "Find contacts tagged VIP",
      "endpoint_hint": "GET /api/v1/getContacts",
      "params": {{"tag": "VIP"}}
    }}
  ]
}}

User request:
{user_input}
""".strip()

    def _load_json(self, raw_response: str) -> dict:
        text = raw_response.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        return json.loads(text)

    def _payload_to_plan(self, user_input: str, payload: dict) -> ExecutionPlan:
        missing_information = self._normalize_missing_information(payload.get("missing_information", []))
        steps = [
            self._normalize_step(raw_step=step, step_number=index + 1)
            for index, step in enumerate(payload.get("steps", []))
            if isinstance(step, dict)
        ]

        if steps:
            status = PlanStatus.READY if not missing_information else PlanStatus.NEEDS_CLARIFICATION
        else:
            status = PlanStatus.NEEDS_CLARIFICATION if missing_information else PlanStatus.UNSUPPORTED

        return ExecutionPlan(
            user_request=user_input,
            summary=self._normalize_summary(payload.get("summary")),
            status=status,
            requires_confirmation=bool(payload.get("requires_confirmation", True)),
            missing_information=missing_information,
            steps=steps,
        )

    def _normalize_step(self, raw_step: dict, step_number: int) -> PlanStep:
        action_name = str(raw_step.get("action", "")).strip()
        action_details = SUPPORTED_ACTIONS.get(action_name, {})

        human_description = str(raw_step.get("description", "")).strip() or "No description provided."
        action_domain = str(raw_step.get("domain", "")).strip() or action_details.get("domain", "unknown")
        endpoint_hint = str(raw_step.get("endpoint_hint", "")).strip() or action_details.get("endpoint_hint")
        action_params = raw_step.get("params", {})

        if not isinstance(action_params, dict):
            action_params = {}

        return PlanStep(
            id=str(raw_step.get("id", f"step-{step_number}")).strip() or f"step-{step_number}",
            domain=action_domain,
            action=action_name,
            description=human_description,
            endpoint_hint=endpoint_hint,
            params=action_params,
        )

    def _normalize_missing_information(self, items: object) -> list[str]:
        if not isinstance(items, list):
            return []

        cleaned_items: list[str] = []
        for item in items:
            text = str(item).strip()
            if text:
                cleaned_items.append(text)
        return cleaned_items

    def _normalize_summary(self, summary: object) -> str:
        clean_summary = str(summary).strip()
        if clean_summary:
            return clean_summary
        return "Generated execution plan."

import re

from wati_agent.domain.models import ExecutionPlan, PlanStatus, PlanStep

SUPPORTED_ACTION_RULES = {
    "get_contacts_by_tag": {
        "required_params": ["tag"],
        "domain": "contacts",
        "endpoint_hint": "GET /api/v1/getContacts",
        "needs_confirmation": False,
    },
    "get_template_by_name": {
        "required_params": ["template_name"],
        "domain": "templates",
        "endpoint_hint": "GET /api/v1/getMessageTemplates",
        "needs_confirmation": False,
    },
    "send_template_message": {
        "required_params": ["template_name"],
        "domain": "messages",
        "endpoint_hint": "POST /api/v1/sendTemplateMessage/{whatsappNumber}",
        "needs_confirmation": True,
    },
    "assign_ticket_to_team": {
        "required_params": ["whatsapp_number", "team_name"],
        "domain": "operators_tickets",
        "endpoint_hint": "POST /api/v1/tickets/assign",
        "needs_confirmation": True,
    },
    "add_tag_to_contact": {
        "required_params": ["whatsapp_number", "tag"],
        "domain": "tags",
        "endpoint_hint": "POST /api/v1/addTag/{whatsappNumber}",
        "needs_confirmation": False,
    },
    "send_broadcast_to_segment": {
        "required_params": ["template_name", "segment_name"],
        "domain": "broadcasts",
        "endpoint_hint": "POST /api/v1/sendBroadcastToSegment",
        "needs_confirmation": True,
    },
}

PARAMETER_ALIASES = {
    "template_name": ["template", "name", "templateName"],
    "whatsapp_number": ["phone", "phone_number", "number", "whatsappNumber"],
    "team_name": ["team", "teamName"],
    "segment_name": ["segment", "segmentName"],
    "broadcast_name": ["broadcast", "broadcastName"],
    "tag": ["tag_name", "tagName"],
}

AMBIGUOUS_REQUEST_HINTS = [
    "customers",
    "people",
    "contacts",
    "someone",
    "somebody",
    "them",
    "this contact",
    "that contact",
    "a reminder",
    "a template",
]


class PlanValidator:
    """Makes sure a plan is usable before we try to execute anything."""

    def validate(self, plan: ExecutionPlan) -> ExecutionPlan:
        clean_missing_information = self._deduplicate_messages(plan.missing_information)

        if not plan.steps:
            if clean_missing_information:
                plan.status = PlanStatus.NEEDS_CLARIFICATION
                plan.missing_information = clean_missing_information
                return plan

            plan.status = PlanStatus.UNSUPPORTED
            plan.missing_information = ["No executable steps were generated."]
            return plan

        validated_steps: list[PlanStep] = []

        for step in plan.steps:
            action_name = step.action.strip()
            if not action_name:
                clean_missing_information.append(f"Step {step.id} is missing an action.")
                continue

            if action_name not in SUPPORTED_ACTION_RULES:
                clean_missing_information.append(
                    f"Step {step.id} uses unsupported action '{action_name}'."
                )
                continue

            validated_steps.append(self._normalize_step(step, plan.user_request))
            clean_missing_information.extend(self._find_missing_params(validated_steps[-1]))

        plan.steps = validated_steps
        clean_missing_information.extend(self._detect_ambiguous_request(plan))
        clean_missing_information = self._deduplicate_messages(clean_missing_information)
        plan.missing_information = clean_missing_information
        plan.requires_confirmation = self._should_require_confirmation(validated_steps)

        if not validated_steps:
            plan.status = PlanStatus.NEEDS_CLARIFICATION if clean_missing_information else PlanStatus.UNSUPPORTED
            return plan

        plan.status = PlanStatus.READY if not clean_missing_information else PlanStatus.NEEDS_CLARIFICATION

        return plan

    def _normalize_step(self, step: PlanStep, user_request: str) -> PlanStep:
        action_rules = SUPPORTED_ACTION_RULES[step.action]
        raw_params = step.params if isinstance(step.params, dict) else {}
        normalized_params = self._normalize_params(raw_params, step.description, user_request)

        return PlanStep(
            id=step.id,
            domain=action_rules["domain"],
            action=step.action,
            description=step.description,
            endpoint_hint=action_rules["endpoint_hint"],
            params=normalized_params,
        )

    def _normalize_params(
        self,
        raw_params: dict[str, object],
        step_description: str,
        user_request: str,
    ) -> dict[str, object]:
        normalized_params = dict(raw_params)

        for canonical_name, aliases in PARAMETER_ALIASES.items():
            if canonical_name in normalized_params and str(normalized_params[canonical_name]).strip():
                continue

            for alias in aliases:
                alias_value = normalized_params.get(alias)
                if alias_value is not None and str(alias_value).strip():
                    normalized_params[canonical_name] = alias_value
                    break

        self._fill_params_from_text(normalized_params, step_description)
        self._fill_params_from_text(normalized_params, user_request)
        return normalized_params

    def _fill_params_from_text(
        self,
        normalized_params: dict[str, object],
        source_text: str,
    ) -> None:
        text = source_text.strip()
        if not text:
            return

        if not normalized_params.get("whatsapp_number"):
            number_match = re.search(r"\b\d{8,15}\b", text)
            if number_match:
                normalized_params["whatsapp_number"] = number_match.group(0)

        if not normalized_params.get("team_name"):
            team_match = re.search(r"\b([A-Z][a-zA-Z]+)\s+team\b", text)
            if team_match:
                normalized_params["team_name"] = team_match.group(1)

        if not normalized_params.get("tag"):
            tag_match = re.search(r"\btag(?:ged)?\s+([A-Za-z0-9_-]+)\b", text, re.IGNORECASE)
            if tag_match:
                normalized_params["tag"] = tag_match.group(1)

        if not normalized_params.get("template_name"):
            template_match = re.search(
                r"\b([A-Za-z0-9_-]+)\s+template\b",
                text,
                re.IGNORECASE,
            )
            if template_match:
                normalized_params["template_name"] = template_match.group(1)

    def _find_missing_params(self, step: PlanStep) -> list[str]:
        required_params = SUPPORTED_ACTION_RULES[step.action]["required_params"]
        missing_params: list[str] = []

        for param_name in required_params:
            param_value = step.params.get(param_name)
            if param_value is None or str(param_value).strip() == "":
                human_param_name = param_name.replace("_", " ")
                missing_params.append(
                    f"Step {step.id} is missing required parameter '{human_param_name}'."
                )

        return missing_params

    def _should_require_confirmation(self, steps: list[PlanStep]) -> bool:
        return any(SUPPORTED_ACTION_RULES[step.action]["needs_confirmation"] for step in steps)

    def _detect_ambiguous_request(self, plan: ExecutionPlan) -> list[str]:
        request_text = plan.user_request.lower().strip()
        ambiguity_messages: list[str] = []

        if plan.steps:
            has_audience_lookup = any(step.action == "get_contacts_by_tag" for step in plan.steps)
            has_message_send = any(
                step.action in {"send_template_message", "send_broadcast_to_segment"}
                for step in plan.steps
            )
            has_broadcast_segment = any(
                step.action == "send_broadcast_to_segment" and step.params.get("segment_name")
                for step in plan.steps
            )

            if (
                has_message_send
                and not has_audience_lookup
                and not has_broadcast_segment
                and "all " not in request_text
            ):
                if any(hint in request_text for hint in ["customers", "people", "contacts", "them"]):
                    ambiguity_messages.append(
                        "The audience is still ambiguous. Please specify who should receive the message."
                    )

            if any(hint in request_text for hint in ["a template", "a reminder"]):
                if not any(step.params.get("template_name") for step in plan.steps):
                    ambiguity_messages.append(
                        "The request does not clearly say which template should be used."
                    )

            if "escalate" in request_text and not any(step.params.get("team_name") for step in plan.steps):
                ambiguity_messages.append(
                    "The request does not clearly say which team should receive the escalation."
                )

        if not plan.steps and any(hint in request_text for hint in AMBIGUOUS_REQUEST_HINTS):
            ambiguity_messages.append(
                "The request is still too broad. Please specify the audience, target contact, or template."
            )

        return ambiguity_messages

    def _deduplicate_messages(self, messages: list[str]) -> list[str]:
        seen_messages: set[str] = set()
        unique_messages: list[str] = []

        for message in messages:
            clean_message = str(message).strip()
            if clean_message and clean_message not in seen_messages:
                seen_messages.add(clean_message)
                unique_messages.append(clean_message)

        return unique_messages

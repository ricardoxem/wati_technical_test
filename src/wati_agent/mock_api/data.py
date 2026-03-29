from copy import deepcopy
from typing import Any

from fastapi import HTTPException

from wati_agent.domain.schemas import (
    ContactRecord,
    OperatorRecord,
    SegmentRecord,
    TeamRecord,
    TemplateRecord,
)

INITIAL_CONTACTS = [
    ContactRecord(
        whatsapp_number="6281234567890",
        name="Alya",
        tags=["VIP", "Renewal"],
        attributes={"city": "Jakarta", "language": "id", "plan": "premium"},
    ),
    ContactRecord(
        whatsapp_number="6281234567891",
        name="Budi",
        tags=["Lead"],
        attributes={"city": "Bandung", "language": "id", "plan": "starter"},
    ),
    ContactRecord(
        whatsapp_number="6281234567892",
        name="Citra",
        tags=["VIP", "Renewal"],
        attributes={"city": "Jakarta", "language": "id", "plan": "business"},
    ),
    ContactRecord(
        whatsapp_number="6281234567893",
        name="Dimas",
        tags=["FlashSale", "Jakarta"],
        attributes={"city": "Jakarta", "language": "id", "plan": "starter"},
    ),
    ContactRecord(
        whatsapp_number="6281234567894",
        name="Eka",
        tags=["VIP", "Support"],
        attributes={"city": "Surabaya", "language": "en", "plan": "premium"},
    ),
]

INITIAL_TEMPLATES = [
    TemplateRecord(name="renewal_reminder", category="utility", parameters=["body_1"]),
    TemplateRecord(name="flash_sale", category="marketing", parameters=["body_1"]),
    TemplateRecord(name="support_follow_up", category="utility", parameters=["body_1"]),
]

INITIAL_OPERATORS = [
    OperatorRecord(email="support@company.com", team_name="Support"),
    OperatorRecord(email="sales@company.com", team_name="Sales"),
    OperatorRecord(email="retention@company.com", team_name="Retention"),
]

INITIAL_TEAMS = [
    TeamRecord(name="Support", operator_emails=["support@company.com"]),
    TeamRecord(name="Sales", operator_emails=["sales@company.com"]),
    TeamRecord(name="Retention", operator_emails=["retention@company.com"]),
]

INITIAL_SEGMENTS = [
    SegmentRecord(
        name="jakarta_customers",
        description="Contacts whose city attribute is Jakarta.",
        contact_numbers=["6281234567890", "6281234567892", "6281234567893"],
    ),
    SegmentRecord(
        name="vip_customers",
        description="Contacts tagged as VIP.",
        contact_numbers=["6281234567890", "6281234567892", "6281234567894"],
    ),
    SegmentRecord(
        name="renewal_candidates",
        description="Contacts likely due for renewal follow-up.",
        contact_numbers=["6281234567890", "6281234567892"],
    ),
]

CONTACTS = [contact.model_copy(deep=True) for contact in INITIAL_CONTACTS]
TEMPLATES = [template.model_copy(deep=True) for template in INITIAL_TEMPLATES]
OPERATORS = [operator.model_copy(deep=True) for operator in INITIAL_OPERATORS]
TEAMS = [team.model_copy(deep=True) for team in INITIAL_TEAMS]
SEGMENTS = [segment.model_copy(deep=True) for segment in INITIAL_SEGMENTS]
MESSAGE_LOG: list[dict[str, Any]] = []
TICKET_LOG: list[dict[str, Any]] = []
BROADCAST_LOG: list[dict[str, Any]] = []


def list_contacts(tag: str | None = None, city: str | None = None) -> list[ContactRecord]:
    matching_contacts = CONTACTS

    if tag:
        matching_contacts = [contact for contact in matching_contacts if tag in contact.tags]

    if city:
        matching_contacts = [
            contact for contact in matching_contacts if contact.attributes.get("city") == city
        ]

    return matching_contacts


def find_contact(whatsapp_number: str) -> ContactRecord:
    for contact in CONTACTS:
        if contact.whatsapp_number == whatsapp_number:
            return contact

    raise HTTPException(status_code=404, detail=f"Contact {whatsapp_number} was not found.")


def find_template(template_name: str) -> TemplateRecord:
    for template in TEMPLATES:
        if template.name == template_name:
            return template

    raise HTTPException(status_code=404, detail=f"Template {template_name} was not found.")


def find_operator_by_team(team_name: str) -> OperatorRecord:
    for operator in OPERATORS:
        if operator.team_name.lower() == team_name.lower():
            return operator

    raise HTTPException(status_code=404, detail=f"Team {team_name} was not found.")


def find_team(team_name: str) -> TeamRecord:
    for team in TEAMS:
        if team.name.lower() == team_name.lower():
            return team

    raise HTTPException(status_code=404, detail=f"Team {team_name} was not found.")


def find_segment(segment_name: str) -> SegmentRecord:
    for segment in SEGMENTS:
        if segment.name.lower() == segment_name.lower():
            return segment

    raise HTTPException(status_code=404, detail=f"Segment {segment_name} was not found.")


def add_tag_to_contact(whatsapp_number: str, tag: str) -> ContactRecord:
    contact = find_contact(whatsapp_number)
    if tag not in contact.tags:
        contact.tags.append(tag)
    return contact


def log_template_message(
    whatsapp_number: str,
    template_name: str,
    broadcast_name: str,
    parameters: list[dict[str, str]],
) -> dict[str, Any]:
    contact = find_contact(whatsapp_number)
    find_template(template_name)

    message_entry = {
        "whatsappNumber": whatsapp_number,
        "contactName": contact.name,
        "template_name": template_name,
        "broadcast_name": broadcast_name,
        "parameters": deepcopy(parameters),
        "status": "accepted",
    }
    MESSAGE_LOG.append(message_entry)
    return message_entry


def assign_ticket(whatsapp_number: str, team_name: str) -> dict[str, Any]:
    contact = find_contact(whatsapp_number)
    operator = find_operator_by_team(team_name)
    team = find_team(team_name)

    ticket_entry = {
        "whatsappNumber": whatsapp_number,
        "contactName": contact.name,
        "teamName": team.name,
        "assignedTo": operator.email,
        "status": "assigned",
    }
    TICKET_LOG.append(ticket_entry)
    return ticket_entry


def send_broadcast(template_name: str, broadcast_name: str, segment_name: str) -> dict[str, Any]:
    find_template(template_name)
    segment = find_segment(segment_name)

    broadcast_entry = {
        "template_name": template_name,
        "broadcast_name": broadcast_name,
        "segmentName": segment.name,
        "audienceSize": len(segment.contact_numbers),
        "status": "queued",
    }
    BROADCAST_LOG.append(broadcast_entry)
    return broadcast_entry

from fastapi import APIRouter
from pydantic import BaseModel

from wati_agent.mock_api.data import assign_ticket

router = APIRouter()


class AssignTicketRequest(BaseModel):
    whatsapp_number: str
    team_name: str


@router.post("/tickets/assign")
def assign_ticket_to_team(payload: AssignTicketRequest) -> dict:
    return assign_ticket(
        whatsapp_number=payload.whatsapp_number,
        team_name=payload.team_name,
    )

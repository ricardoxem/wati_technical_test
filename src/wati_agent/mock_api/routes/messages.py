from fastapi import APIRouter
from pydantic import BaseModel, Field

from wati_agent.mock_api.data import log_template_message

router = APIRouter()


class TemplateMessageRequest(BaseModel):
    template_name: str
    broadcast_name: str
    parameters: list[dict[str, str]] = Field(default_factory=list)


@router.post("/sendTemplateMessage/{whatsapp_number}")
def send_template_message(whatsapp_number: str, payload: TemplateMessageRequest) -> dict:
    message_entry = log_template_message(
        whatsapp_number=whatsapp_number,
        template_name=payload.template_name,
        broadcast_name=payload.broadcast_name,
        parameters=payload.parameters,
    )
    return message_entry

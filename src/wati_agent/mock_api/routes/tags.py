from fastapi import APIRouter
from pydantic import BaseModel

from wati_agent.mock_api.data import add_tag_to_contact

router = APIRouter()


class AddTagRequest(BaseModel):
    tag: str


@router.post("/addTag/{whatsapp_number}")
def add_tag(whatsapp_number: str, payload: AddTagRequest) -> dict:
    updated_contact = add_tag_to_contact(whatsapp_number=whatsapp_number, tag=payload.tag)
    return {
        "status": "updated",
        "whatsappNumber": whatsapp_number,
        "tags": updated_contact.tags,
    }

from fastapi import APIRouter
from pydantic import BaseModel

from wati_agent.mock_api.data import send_broadcast

router = APIRouter()


class BroadcastRequest(BaseModel):
    template_name: str
    broadcast_name: str
    segment_name: str


@router.post("/sendBroadcastToSegment")
def send_broadcast_to_segment(payload: BroadcastRequest) -> dict:
    return send_broadcast(
        template_name=payload.template_name,
        broadcast_name=payload.broadcast_name,
        segment_name=payload.segment_name,
    )

from fastapi import APIRouter

from wati_agent.mock_api.data import OPERATORS

router = APIRouter()


@router.get("/getOperators")
def get_operators() -> dict:
    return {"operators": [operator.model_dump() for operator in OPERATORS]}

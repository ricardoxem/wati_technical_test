from fastapi import APIRouter, Query

from wati_agent.mock_api.data import find_contact, list_contacts

router = APIRouter()


@router.get("/getContacts")
def get_contacts(
    page_size: int = Query(default=20, alias="pageSize"),
    page_number: int = Query(default=1, alias="pageNumber"),
    tag: str | None = Query(default=None),
    city: str | None = Query(default=None),
) -> dict:
    matching_contacts = list_contacts(tag=tag, city=city)
    start_index = max(page_number - 1, 0) * page_size
    end_index = start_index + page_size
    paged_contacts = matching_contacts[start_index:end_index]

    return {
        "pageSize": page_size,
        "pageNumber": page_number,
        "total": len(matching_contacts),
        "contacts": [contact.model_dump() for contact in paged_contacts],
    }


@router.get("/getContactInfo/{whatsapp_number}")
def get_contact_info(whatsapp_number: str) -> dict:
    contact = find_contact(whatsapp_number)
    return contact.model_dump()

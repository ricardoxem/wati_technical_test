from fastapi import APIRouter, Query

from wati_agent.mock_api.data import TEMPLATES, find_template

router = APIRouter()


@router.get("/getMessageTemplates")
def get_templates(
    page_size: int = Query(default=20, alias="pageSize"),
    page_number: int = Query(default=1, alias="pageNumber"),
    template_name: str | None = Query(default=None, alias="templateName"),
) -> dict:
    matching_templates = TEMPLATES
    if template_name:
        matching_templates = [find_template(template_name)]

    start_index = max(page_number - 1, 0) * page_size
    end_index = start_index + page_size
    paged_templates = matching_templates[start_index:end_index]

    return {
        "pageSize": page_size,
        "pageNumber": page_number,
        "total": len(matching_templates),
        "templates": [template.model_dump() for template in paged_templates],
    }

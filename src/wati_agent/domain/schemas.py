from pydantic import BaseModel, Field


class ContactRecord(BaseModel):
    whatsapp_number: str
    name: str
    tags: list[str] = Field(default_factory=list)
    attributes: dict[str, str] = Field(default_factory=dict)


class TemplateRecord(BaseModel):
    name: str
    category: str = "marketing"
    parameters: list[str] = Field(default_factory=list)


class OperatorRecord(BaseModel):
    email: str
    team_name: str


class TeamRecord(BaseModel):
    name: str
    operator_emails: list[str] = Field(default_factory=list)


class SegmentRecord(BaseModel):
    name: str
    description: str
    contact_numbers: list[str] = Field(default_factory=list)

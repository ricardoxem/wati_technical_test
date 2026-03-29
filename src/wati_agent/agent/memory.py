from pydantic import BaseModel, Field


class SessionMemory(BaseModel):
    """Very small in-memory history for the current CLI session."""

    previous_requests: list[str] = Field(default_factory=list)

    def remember(self, user_input: str) -> None:
        self.previous_requests.append(user_input)

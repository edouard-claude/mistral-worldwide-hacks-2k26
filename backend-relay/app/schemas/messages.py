import re

from pydantic import BaseModel, field_validator

SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


class InitSessionInput(BaseModel):
    session_id: str

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        if not SESSION_ID_PATTERN.match(v):
            raise ValueError("Invalid session_id format")
        return v


class SubmitNewsInput(BaseModel):
    session_id: str
    content: str

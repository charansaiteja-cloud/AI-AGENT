from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from backend.app.schemas.common import ORMModel


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    status: str | None = Field(default=None, pattern="^(active|archived)$")


class ConversationOut(ORMModel):
    id: int
    customer_id: int
    title: str
    status: str
    created_at: datetime
    updated_at: datetime


class ConversationSummary(ConversationOut):
    message_count: int = 0
    last_message: str | None = None
    last_message_at: datetime | None = None

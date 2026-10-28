from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from backend.app.schemas.common import ORMModel


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be empty")
        return value


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be empty")
        return value


class CustomerOut(ORMModel):
    id: int
    name: str
    email: str | None
    created_at: datetime
    conversation_count: int = 0
    last_activity_at: datetime | None = None

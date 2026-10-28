from datetime import datetime

from pydantic import BaseModel

from backend.app.schemas.common import ORMModel


class MemoryOut(ORMModel):
    id: str
    text: str
    kind: str = "other"
    source: str = "memory"
    context: str | None = None
    created_at: datetime | None = None
    score: float | None = None


class MemoryListResponse(BaseModel):
    customer_id: int
    available: bool
    count: int
    memories: list[MemoryOut] = []
    error: str | None = None

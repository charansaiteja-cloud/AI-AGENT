from datetime import datetime

from backend.app.schemas.attachment import AttachmentOut
from backend.app.schemas.common import ORMModel


class MessageOut(ORMModel):
    id: int
    conversation_id: int
    role: str
    content: str
    model: str | None
    memory_count: int = 0
    created_at: datetime
    attachments: list[AttachmentOut] = []


class MessageListResponse(ORMModel):
    conversation_id: int
    messages: list[MessageOut]

from datetime import datetime

from backend.app.schemas.common import ORMModel


class AttachmentOut(ORMModel):
    id: int
    conversation_id: int
    message_id: int | None
    original_filename: str
    content_type: str
    file_size: int
    created_at: datetime
    download_url: str | None = None

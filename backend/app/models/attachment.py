from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.database import Base


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id"),
        index=True,
    )

    message_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id"),
        nullable=True,
        index=True,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255)
    )

    stored_filename: Mapped[str] = mapped_column(
        String(255),
        unique=True,
    )

    content_type: Mapped[str] = mapped_column(
        String(100)
    )

    file_size: Mapped[int] = mapped_column(
        Integer
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

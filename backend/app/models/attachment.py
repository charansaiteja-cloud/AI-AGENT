from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.database import Base
from backend.app.models.base import utcnow
from backend.app.models.types import UTCDateTime

if TYPE_CHECKING:
    from backend.app.models.conversation import Conversation
    from backend.app.models.message import Message


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(primary_key=True)

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
    )

    message_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
    )

    stored_filename: Mapped[str] = mapped_column(
        String(255),
        unique=True,
    )

    content_type: Mapped[str] = mapped_column(
        String(100),
    )

    file_size: Mapped[int] = mapped_column(
        Integer,
    )

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=utcnow,
    )

    conversation: Mapped[Conversation] = relationship(back_populates="attachments")
    message: Mapped[Message | None] = relationship(back_populates="attachments")

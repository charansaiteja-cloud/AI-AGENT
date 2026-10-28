from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.database import Base
from backend.app.models.base import utcnow
from backend.app.models.types import UTCDateTime

if TYPE_CHECKING:
    from backend.app.models.conversation import Conversation


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(primary_key=True)

    # The memory key is deliberately separate from the database id. It is
    # used as the Hindsight bank identifier so deleting and recreating a
    # customer can never inherit another customer's memories.
    memory_key: Mapped[str] = mapped_column(
        String(64),
        default=lambda: uuid.uuid4().hex,
        unique=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        default="Anonymous Customer",
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=utcnow,
    )

    conversations: Mapped[list[Conversation]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

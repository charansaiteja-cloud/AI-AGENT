from backend.app.models.attachment import Attachment
from backend.app.models.customer import Customer
from backend.app.models.message import Message
from backend.app.schemas.attachment import AttachmentOut
from backend.app.schemas.customer import CustomerOut
from backend.app.schemas.memory import MemoryOut
from backend.app.schemas.message import MessageOut
from backend.app.services.hindsight import MemoryRecord


def attachment_out(attachment: Attachment) -> AttachmentOut:
    return AttachmentOut(
        id=attachment.id,
        conversation_id=attachment.conversation_id,
        message_id=attachment.message_id,
        original_filename=attachment.original_filename,
        content_type=attachment.content_type,
        file_size=attachment.file_size,
        created_at=attachment.created_at,
        download_url=f"/api/attachments/{attachment.id}",
    )


def message_out(
    message: Message,
    attachments: list[Attachment] | None = None,
) -> MessageOut:
    return MessageOut(
        id=message.id,
        conversation_id=message.conversation_id,
        role=message.role,
        content=message.content,
        model=message.model,
        memory_count=message.memory_count,
        created_at=message.created_at,
        attachments=[attachment_out(item) for item in (attachments or [])],
    )


def customer_out(
    customer: Customer,
    conversation_count: int = 0,
    last_activity_at=None,
) -> CustomerOut:
    return CustomerOut(
        id=customer.id,
        name=customer.name,
        email=customer.email,
        created_at=customer.created_at,
        conversation_count=conversation_count,
        last_activity_at=last_activity_at,
    )


def memory_out(record: MemoryRecord) -> MemoryOut:
    return MemoryOut(
        id=record.id,
        text=record.text,
        kind=record.kind,
        source=record.source,
        context=record.context,
        created_at=record.created_at,
        score=record.score,
    )

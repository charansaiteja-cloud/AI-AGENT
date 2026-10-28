from __future__ import annotations

from collections import defaultdict

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_attachment_service
from backend.app.api.serializers import attachment_out, message_out
from backend.app.db.database import get_db
from backend.app.models.attachment import Attachment
from backend.app.models.conversation import Conversation
from backend.app.models.message import Message
from backend.app.schemas.attachment import AttachmentOut
from backend.app.schemas.conversation import ConversationOut, ConversationUpdate
from backend.app.schemas.message import MessageListResponse
from backend.app.services.attachments import AttachmentError, AttachmentService

router = APIRouter(tags=["conversations"])


async def _get_conversation_or_404(
    db: AsyncSession,
    conversation_id: int,
) -> Conversation:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
) -> ConversationOut:
    conversation = await _get_conversation_or_404(db, conversation_id)
    return ConversationOut.model_validate(conversation)


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut)
async def update_conversation(
    conversation_id: int,
    request: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
) -> ConversationOut:
    conversation = await _get_conversation_or_404(db, conversation_id)

    if request.title is not None:
        conversation.title = request.title
    if request.status is not None:
        conversation.status = request.status

    await db.commit()
    await db.refresh(conversation)
    return ConversationOut.model_validate(conversation)


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    attachments: AttachmentService = Depends(get_attachment_service),
) -> Response:
    await _get_conversation_or_404(db, conversation_id)

    attachment_rows = (
        await db.scalars(select(Attachment).where(Attachment.conversation_id == conversation_id))
    ).all()

    for attachment in attachment_rows:
        attachments.delete_file(
            attachment.conversation_id,
            attachment.stored_filename,
        )

    await db.execute(delete(Attachment).where(Attachment.conversation_id == conversation_id))
    await db.execute(delete(Message).where(Message.conversation_id == conversation_id))
    await db.execute(delete(Conversation).where(Conversation.id == conversation_id))
    await db.commit()

    attachments.delete_conversation_files(conversation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=MessageListResponse,
)
async def get_messages(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
) -> MessageListResponse:
    await _get_conversation_or_404(db, conversation_id)

    messages = (
        await db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        )
    ).all()

    attachment_rows = (
        await db.scalars(
            select(Attachment)
            .where(Attachment.conversation_id == conversation_id)
            .order_by(Attachment.created_at.asc(), Attachment.id.asc())
        )
    ).all()

    by_message: dict[int, list[Attachment]] = defaultdict(list)
    for attachment in attachment_rows:
        if attachment.message_id is not None:
            by_message[attachment.message_id].append(attachment)

    return MessageListResponse(
        conversation_id=conversation_id,
        messages=[message_out(message, by_message.get(message.id, [])) for message in messages],
    )


@router.get(
    "/conversations/{conversation_id}/attachments",
    response_model=list[AttachmentOut],
)
async def list_attachments(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[AttachmentOut]:
    await _get_conversation_or_404(db, conversation_id)

    rows = (
        await db.scalars(
            select(Attachment)
            .where(Attachment.conversation_id == conversation_id)
            .order_by(Attachment.created_at.asc(), Attachment.id.asc())
        )
    ).all()

    return [attachment_out(item) for item in rows]


@router.post(
    "/conversations/{conversation_id}/attachments",
    response_model=AttachmentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    conversation_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    attachments: AttachmentService = Depends(get_attachment_service),
) -> AttachmentOut:
    await _get_conversation_or_404(db, conversation_id)

    try:
        stored = await attachments.save_upload(file, conversation_id)
    except AttachmentError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc

    attachment = Attachment(
        conversation_id=conversation_id,
        original_filename=stored.original_filename,
        stored_filename=stored.stored_filename,
        content_type=stored.content_type,
        file_size=stored.file_size,
    )
    db.add(attachment)

    try:
        await db.commit()
        await db.refresh(attachment)
    except Exception:
        await db.rollback()
        attachments.delete_file(conversation_id, stored.stored_filename)
        raise

    return attachment_out(attachment)


@router.get("/attachments/{attachment_id}")
async def download_attachment(
    attachment_id: int,
    inline: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    attachments: AttachmentService = Depends(get_attachment_service),
) -> FileResponse:
    attachment = await db.get(Attachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found")

    path = attachments.path_for(
        attachment.conversation_id,
        attachment.stored_filename,
    )
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Attachment file not found")

    disposition = (
        "inline" if inline and attachment.content_type.startswith("image/") else "attachment"
    )

    return FileResponse(
        path,
        media_type=attachment.content_type,
        filename=attachment.original_filename,
        content_disposition_type=disposition,
    )


@router.delete(
    "/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_attachment(
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    attachments: AttachmentService = Depends(get_attachment_service),
) -> Response:
    attachment = await db.get(Attachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found")

    attachments.delete_file(
        attachment.conversation_id,
        attachment.stored_filename,
    )
    await db.delete(attachment)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)

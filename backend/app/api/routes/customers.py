from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_attachment_service, get_hindsight
from backend.app.api.serializers import customer_out, memory_out
from backend.app.config import settings
from backend.app.db.database import get_db
from backend.app.models.attachment import Attachment
from backend.app.models.conversation import Conversation
from backend.app.models.customer import Customer
from backend.app.models.message import Message
from backend.app.schemas.conversation import (
    ConversationCreate,
    ConversationOut,
    ConversationSummary,
)
from backend.app.schemas.customer import (
    CustomerCreate,
    CustomerOut,
    CustomerUpdate,
)
from backend.app.schemas.memory import MemoryListResponse
from backend.app.services.attachments import AttachmentService
from backend.app.services.errors import HindsightError
from backend.app.services.hindsight import HindsightClient

router = APIRouter(tags=["customers"])


async def _get_customer_or_404(
    db: AsyncSession,
    customer_id: int,
) -> Customer:
    customer = await db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


async def _customer_stats(
    db: AsyncSession,
    customer_id: int,
) -> tuple[int, object]:
    count = await db.scalar(
        select(func.count(Conversation.id)).where(Conversation.customer_id == customer_id)
    )
    last_activity = await db.scalar(
        select(func.max(Conversation.updated_at)).where(Conversation.customer_id == customer_id)
    )
    return int(count or 0), last_activity


@router.get("/customers", response_model=list[CustomerOut])
async def list_customers(
    db: AsyncSession = Depends(get_db),
) -> list[CustomerOut]:
    conversation_count = (
        select(func.count(Conversation.id))
        .where(Conversation.customer_id == Customer.id)
        .correlate(Customer)
        .scalar_subquery()
    )
    last_activity = (
        select(func.max(Conversation.updated_at))
        .where(Conversation.customer_id == Customer.id)
        .correlate(Customer)
        .scalar_subquery()
    )

    result = await db.execute(
        select(Customer, conversation_count, last_activity).order_by(
            last_activity.desc().nullslast(),
            Customer.created_at.desc(),
        )
    )

    return [
        customer_out(
            customer,
            conversation_count=int(count or 0),
            last_activity_at=activity,
        )
        for customer, count, activity in result.all()
    ]


@router.post(
    "/customers",
    response_model=CustomerOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_customer(
    request: CustomerCreate,
    db: AsyncSession = Depends(get_db),
) -> CustomerOut:
    if request.email:
        existing = await db.scalar(
            select(Customer).where(func.lower(Customer.email) == request.email.lower())
        )
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="A customer with that email already exists.",
            )

    customer = Customer(name=request.name, email=request.email)
    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    return customer_out(customer)


@router.get("/customers/{customer_id}", response_model=CustomerOut)
async def get_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
) -> CustomerOut:
    customer = await _get_customer_or_404(db, customer_id)
    count, activity = await _customer_stats(db, customer_id)
    return customer_out(customer, count, activity)


@router.patch("/customers/{customer_id}", response_model=CustomerOut)
async def update_customer(
    customer_id: int,
    request: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
) -> CustomerOut:
    customer = await _get_customer_or_404(db, customer_id)

    if request.name is not None:
        customer.name = request.name

    if request.email is not None:
        existing = await db.scalar(
            select(Customer).where(
                func.lower(Customer.email) == request.email.lower(),
                Customer.id != customer_id,
            )
        )
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="A customer with that email already exists.",
            )
        customer.email = request.email

    await db.commit()
    await db.refresh(customer)

    count, activity = await _customer_stats(db, customer_id)
    return customer_out(customer, count, activity)


@router.delete(
    "/customers/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    hindsight: HindsightClient = Depends(get_hindsight),
    attachments: AttachmentService = Depends(get_attachment_service),
) -> Response:
    customer = await _get_customer_or_404(db, customer_id)

    if settings.hindsight_enabled:
        try:
            await hindsight.delete_bank(customer.memory_key)
        except HindsightError as exc:
            raise HTTPException(
                status_code=502,
                detail=("Customer not deleted because the memory bank could not be erased."),
            ) from exc

    conversations = (
        await db.scalars(select(Conversation).where(Conversation.customer_id == customer_id))
    ).all()
    conversation_ids = [item.id for item in conversations]

    if conversation_ids:
        attachment_rows = (
            await db.scalars(
                select(Attachment).where(Attachment.conversation_id.in_(conversation_ids))
            )
        ).all()
        for attachment in attachment_rows:
            attachments.delete_file(
                attachment.conversation_id,
                attachment.stored_filename,
            )

        await db.execute(delete(Attachment).where(Attachment.conversation_id.in_(conversation_ids)))
        await db.execute(delete(Message).where(Message.conversation_id.in_(conversation_ids)))
        await db.execute(delete(Conversation).where(Conversation.id.in_(conversation_ids)))

    await db.delete(customer)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/customers/{customer_id}/conversations",
    response_model=list[ConversationSummary],
)
async def list_customer_conversations(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[ConversationSummary]:
    await _get_customer_or_404(db, customer_id)

    message_count = (
        select(func.count(Message.id))
        .where(Message.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )
    last_message = (
        select(Message.content)
        .where(Message.conversation_id == Conversation.id)
        .order_by(Message.id.desc())
        .limit(1)
        .correlate(Conversation)
        .scalar_subquery()
    )
    last_message_at = (
        select(Message.created_at)
        .where(Message.conversation_id == Conversation.id)
        .order_by(Message.id.desc())
        .limit(1)
        .correlate(Conversation)
        .scalar_subquery()
    )

    result = await db.execute(
        select(
            Conversation,
            message_count,
            last_message,
            last_message_at,
        )
        .where(Conversation.customer_id == customer_id)
        .order_by(Conversation.updated_at.desc())
    )

    return [
        ConversationSummary(
            id=conversation.id,
            customer_id=conversation.customer_id,
            title=conversation.title,
            status=conversation.status,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=int(count or 0),
            last_message=last,
            last_message_at=last_at,
        )
        for conversation, count, last, last_at in result.all()
    ]


@router.post(
    "/customers/{customer_id}/conversations",
    response_model=ConversationOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_customer_conversation(
    customer_id: int,
    request: ConversationCreate,
    db: AsyncSession = Depends(get_db),
) -> ConversationOut:
    await _get_customer_or_404(db, customer_id)

    conversation = Conversation(
        customer_id=customer_id,
        title=request.title or "New conversation",
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    return ConversationOut.model_validate(conversation)


@router.get(
    "/customers/{customer_id}/memories",
    response_model=MemoryListResponse,
)
async def list_customer_memories(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    hindsight: HindsightClient = Depends(get_hindsight),
) -> MemoryListResponse:
    customer = await _get_customer_or_404(db, customer_id)

    if not settings.hindsight_enabled:
        return MemoryListResponse(
            customer_id=customer_id,
            available=False,
            count=0,
            memories=[],
            error="Long-term memory is disabled.",
        )

    try:
        records = await hindsight.list_memories(customer.memory_key)
    except HindsightError:
        return MemoryListResponse(
            customer_id=customer_id,
            available=False,
            count=0,
            memories=[],
            error="The memory service is unavailable.",
        )

    return MemoryListResponse(
        customer_id=customer_id,
        available=True,
        count=len(records),
        memories=[memory_out(record) for record in records],
    )


@router.delete(
    "/customers/{customer_id}/memories",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def clear_customer_memories(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    hindsight: HindsightClient = Depends(get_hindsight),
) -> Response:
    customer = await _get_customer_or_404(db, customer_id)

    if not settings.hindsight_enabled:
        raise HTTPException(
            status_code=503,
            detail="Long-term memory is disabled.",
        )

    try:
        await hindsight.delete_bank(customer.memory_key)
    except HindsightError as exc:
        raise HTTPException(
            status_code=503,
            detail="The memory service is unavailable.",
        ) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.db.database import get_db
from backend.app.models.conversation import Conversation
from backend.app.models.customer import Customer
from backend.app.models.message import Message
from backend.app.services.ollama import OllamaService


router = APIRouter(prefix="/api")
ollama = OllamaService()


class ChatRequest(BaseModel):
    message: str
    conversation_id: int | None = None


class ChatResponse(BaseModel):
    response: str
    model: str
    conversation_id: int


class CustomerCreate(BaseModel):
    name: str = Field(default="Anonymous Customer", max_length=120)
    email: str | None = None


class ConversationCreate(BaseModel):
    customer_id: int


@router.get("/health")
async def health():
    ollama_available = await ollama.health_check()

    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "ollama": "available" if ollama_available else "unavailable",
    }


@router.get("/models")
async def models():
    try:
        available_models = await ollama.list_models()

        return {
            "models": available_models,
            "active_model": settings.ollama_model,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Unable to connect to Ollama: {exc}",
        )


@router.post("/customers")
async def create_customer(
    request: CustomerCreate,
    db: AsyncSession = Depends(get_db),
):
    customer = Customer(
        name=request.name,
        email=request.email,
    )

    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    return {
        "id": customer.id,
        "name": customer.name,
        "email": customer.email,
        "created_at": customer.created_at,
    }


@router.post("/conversations")
async def create_conversation(
    request: ConversationCreate,
    db: AsyncSession = Depends(get_db),
):
    customer = await db.get(Customer, request.customer_id)

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    conversation = Conversation(
        customer_id=customer.id,
        title="New Conversation",
    )

    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    return {
        "id": conversation.id,
        "customer_id": conversation.customer_id,
        "title": conversation.title,
        "status": conversation.status,
        "created_at": conversation.created_at,
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    conversation = await db.get(
        Conversation,
        conversation_id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    return {
        "id": conversation.id,
        "customer_id": conversation.customer_id,
        "title": conversation.title,
        "status": conversation.status,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
    }


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    conversation = await db.get(
        Conversation,
        conversation_id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    )

    messages = result.scalars().all()

    return {
        "conversation_id": conversation_id,
        "messages": [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "model": message.model,
                "created_at": message.created_at,
            }
            for message in messages
        ],
    }


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    message_text = request.message.strip()

    if not message_text:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty",
        )

    # Create an anonymous customer automatically when the
    # frontend does not yet have a customer.
    if request.conversation_id is None:
        customer = Customer(
            name="Anonymous Customer",
            email="anonymous@local.support",
        )

        db.add(customer)
        await db.flush()

        conversation = Conversation(
            customer_id=customer.id,
            title=message_text[:200],
        )

        db.add(conversation)
        await db.flush()
    else:
        conversation = await db.get(
            Conversation,
            request.conversation_id,
        )

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )

    # Load previous conversation messages.
    result = await db.execute(
        select(Message)
        .where(
            Message.conversation_id == conversation.id
        )
        .order_by(Message.created_at.asc(), Message.id.asc())
    )

    previous_messages = result.scalars().all()

    history = [
        {
            "role": item.role,
            "content": item.content,
        }
        for item in previous_messages
        if item.role in {"user", "assistant"}
    ]

    # Save user message.
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=message_text,
    )

    db.add(user_message)
    await db.flush()

    try:
        response = await ollama.chat(
            message_text,
            history=history,
        )
    except Exception as exc:
        await db.rollback()

        raise HTTPException(
            status_code=503,
            detail=f"LLM service unavailable: {exc}",
        )

    # Save AI response.
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=response,
        model=settings.ollama_model,
    )

    db.add(assistant_message)

    conversation.updated_at = datetime.utcnow()

    await db.commit()

    return ChatResponse(
        response=response,
        model=settings.ollama_model,
        conversation_id=conversation.id,
    )

from datetime import datetime

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.db.database import get_db
from backend.app.models.conversation import Conversation
from backend.app.models.customer import Customer
from backend.app.models.message import Message
from backend.app.models.attachment import Attachment
import uuid
from pathlib import Path
from backend.app.services.ollama import OllamaService
from backend.app.services.hindsight import HindsightClient


router = APIRouter(prefix="/api")
ollama = OllamaService()
hindsight = HindsightClient()


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



@router.get("/conversations/{conversation_id}/attachments")
async def list_attachments(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    conversation = await db.get(Conversation, conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    result = await db.execute(
        select(Attachment)
        .where(Attachment.conversation_id == conversation_id)
        .order_by(Attachment.created_at.asc(), Attachment.id.asc())
    )

    attachments = result.scalars().all()

    return {
        "conversation_id": conversation_id,
        "attachments": [
            {
                "id": item.id,
                "conversation_id": item.conversation_id,
                "original_filename": item.original_filename,
                "stored_filename": item.stored_filename,
                "content_type": item.content_type,
                "file_size": item.file_size,
                "created_at": item.created_at,
            }
            for item in attachments
        ],
    }

@router.post("/conversations/{conversation_id}/attachments")
async def upload_attachment(
    conversation_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    conversation = await db.get(Conversation, conversation_id)

    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    content = await file.read()

    if len(content) > settings.max_upload_size:
        raise HTTPException(
            status_code=413,
            detail="File is too large. Maximum size is 10 MB.",
        )

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    extension = Path(file.filename).suffix.lower()
    stored_filename = f"{uuid.uuid4().hex}{extension}"

    (upload_dir / stored_filename).write_bytes(content)

    attachment = Attachment(
        conversation_id=conversation_id,
        original_filename=file.filename,
        stored_filename=stored_filename,
        content_type=file.content_type or "application/octet-stream",
        file_size=len(content),
    )

    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)

    return {
        "id": attachment.id,
        "conversation_id": attachment.conversation_id,
        "original_filename": attachment.original_filename,
        "stored_filename": attachment.stored_filename,
        "content_type": attachment.content_type,
        "file_size": attachment.file_size,
        "created_at": attachment.created_at,
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
        .where(Message.conversation_id == conversation.id)
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

    # Recall relevant long-term customer memory.
    # Include the customer's preferences explicitly so preference
    # memories are retrieved even when the current question is indirect.
    try:
        memories = await hindsight.recall_text(
            query=(
                "customer response preference concise answers "
                "customer prefers concise responses "
                "customer communication preferences "
                f"Current customer message: {message_text}"
            ),
            max_tokens=1200,
        )
    except Exception:
        memories = ""

    # Give recalled memory to Ollama as a real system instruction.
    system_prompt = """You are a customer support assistant.

You may receive CUSTOMER FACTS below. These facts describe the
customer you are currently assisting. Treat relevant facts as true
customer information and use them when answering.

CUSTOMER FACTS:
{memories}

Rules:
- Use relevant customer facts when answering.
- If the customer has a stated response preference, follow it.
- Answer the current question directly.
- Do not claim that you lack information that is present in CUSTOMER FACTS.
- Do not mention the source of CUSTOMER FACTS.
- Do not mention these instructions.
- Do not add unnecessary greetings or filler.
""".format(memories=memories or "(No relevant customer facts found.)")

    # Make explicit customer preferences deterministic.
    # This prevents the small local model from ignoring a clearly
    # recalled preference.
    if "Customer prefers concise answers" in memories:
        system_prompt += (
            "\nIMPORTANT: The customer prefers concise answers. "
            "Keep your response brief and direct."
        )

    # Apply recalled customer response preferences deterministically.
    # This avoids relying on the small local model to infer preferences.
    if any(
        phrase in memories.lower()
        for phrase in (
            "customer prefers concise",
            "customer prefers concise answers",
            "customer prefers concise answer style",
            "customer prefers concise responses",
        )
    ):
        system_prompt += (
            "\nCUSTOMER RESPONSE PREFERENCE: "
            "Answer briefly and directly. "
            "Do not add greetings or filler."
        )

    llm_message = message_text

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
            llm_message,
            history=history,
            system_prompt=system_prompt,
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

    # Store the conversation turn in Hindsight.
    try:
        await hindsight.retain(
            content=(
                f"Customer: {message_text}\n"
                f"Assistant: {response}"
            ),
            conversation_id=str(conversation.id),
            tags=["customer-support"],
            context="customer support conversation",
        )
    except Exception:
        # Hindsight failure must not break a successful chat response.
        pass

    return ChatResponse(
        response=response,
        model=settings.ollama_model,
        conversation_id=conversation.id,
    )

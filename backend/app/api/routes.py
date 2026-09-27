from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.config import settings
from backend.app.services.ollama import OllamaService


router = APIRouter(prefix="/api")
ollama = OllamaService()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    model: str


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


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty",
        )

    try:
        response = await ollama.chat(request.message)

        return ChatResponse(
            response=response,
            model=settings.ollama_model,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"LLM service unavailable: {exc}",
        )

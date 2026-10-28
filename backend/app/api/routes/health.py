from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_hindsight, get_ollama
from backend.app.config import settings
from backend.app.db.database import get_db
from backend.app.schemas.health import HealthResponse, ModelListResponse
from backend.app.services.errors import OllamaError
from backend.app.services.hindsight import HindsightClient
from backend.app.services.ollama import OllamaService

router = APIRouter(tags=["system"])


async def _database_ok(db: AsyncSession) -> bool:
    try:
        await db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@router.get("/health", response_model=HealthResponse)
async def health(
    db: AsyncSession = Depends(get_db),
    ollama: OllamaService = Depends(get_ollama),
    hindsight: HindsightClient = Depends(get_hindsight),
) -> HealthResponse:
    database_ok, ollama_ok, hindsight_ok = await asyncio.gather(
        _database_ok(db),
        ollama.health_check(),
        hindsight.health_check(),
    )

    return HealthResponse(
        status="ok" if database_ok and ollama_ok else "degraded",
        service=settings.app_name,
        version=settings.app_version,
        database="connected" if database_ok else "unavailable",
        ollama="available" if ollama_ok else "unavailable",
        hindsight="available" if hindsight_ok else "unavailable",
        model=settings.ollama_model,
    )


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness(
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    if not await _database_ok(db):
        raise HTTPException(
            status_code=503,
            detail="Database is not ready",
        )
    return {"status": "ready"}


@router.get("/models", response_model=ModelListResponse)
async def models(
    ollama: OllamaService = Depends(get_ollama),
) -> ModelListResponse:
    try:
        available_models = await ollama.list_models()
    except OllamaError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    return ModelListResponse(
        models=available_models,
        active_model=settings.ollama_model,
    )

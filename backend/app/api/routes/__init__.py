from fastapi import APIRouter

from backend.app.api.routes import chat, conversations, customers, demo, health

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(customers.router)
api_router.include_router(conversations.router)
api_router.include_router(chat.router)
api_router.include_router(demo.router)

__all__ = ["api_router"]

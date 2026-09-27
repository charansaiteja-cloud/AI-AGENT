from fastapi import FastAPI

from backend.app.config import settings
from backend.app.api.routes import router


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)

app.include_router(router)


@app.get("/")
async def root():
    return {
        "message": "Customer Support Agent API",
        "version": settings.app_version,
    }

from __future__ import annotations

import logging
import secrets
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.api.deps import rate_limiter
from backend.app.api.routes import api_router
from backend.app.config import settings
from backend.app.db.database import dispose_db, init_db

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id
        started = time.perf_counter()

        response = await call_next(request)
        duration_ms = int((time.perf_counter() - started) * 1000)
        response.headers["X-Request-ID"] = request_id

        if request.url.path not in {"/api/health", "/api/health/live"}:
            logger.info(
                "%s %s -> %s (%sms) [%s]",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                request_id,
            )

        return response


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Optional shared-secret authentication for every /api route.

    Health endpoints stay open so container orchestrators can probe the
    service. When ``APP_API_KEY`` is unset, the middleware is a no-op, which
    keeps local development and the bundled demo unchanged.
    """

    @staticmethod
    def _is_public(path: str) -> bool:
        prefix = settings.api_prefix
        return path in {
            f"{prefix}/health",
            f"{prefix}/health/live",
            f"{prefix}/health/ready",
        }

    async def dispatch(self, request: Request, call_next):
        configured_key = settings.app_api_key
        if (
            not configured_key
            or request.method == "OPTIONS"
            or self._is_public(request.url.path)
            or not request.url.path.startswith(settings.api_prefix)
        ):
            return await call_next(request)

        provided = request.headers.get("X-API-Key", "")
        if not secrets.compare_digest(provided, configured_key):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key."},
                headers={"WWW-Authenticate": "ApiKey"},
            )

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "img-src 'self' data: blob:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'",
        )

        if settings.is_production and request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.rate_limit_enabled or request.method != "POST":
            return await call_next(request)

        path = request.url.path
        if path == f"{settings.api_prefix}/chat":
            scope = "chat"
            limit = settings.rate_limit_chat_per_minute
        elif path.startswith(f"{settings.api_prefix}/conversations/") and path.endswith(
            "/attachments"
        ):
            scope = "upload"
            limit = settings.rate_limit_upload_per_minute
        else:
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        allowed, retry_after = rate_limiter.check(
            f"{scope}:{client}",
            limit=limit,
        )

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please wait a moment and retry."},
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        return response


def _mount_frontend(app: FastAPI) -> None:
    static_root = settings.static_dir
    assets_dir = static_root / "assets"
    index_file = static_root / "index.html"

    if assets_dir.is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=assets_dir),
            name="assets",
        )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")

        if index_file.is_file():
            resolved_root = static_root.resolve()
            candidate = (static_root / full_path).resolve()

            if candidate.is_file() and resolved_root in candidate.parents:
                return FileResponse(candidate)

            return FileResponse(index_file)

        raise HTTPException(status_code=404, detail="Frontend build not found")


def create_app() -> FastAPI:
    _configure_logging()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        await init_db()
        logger.info(
            "%s v%s started (memory=%s, model=%s)",
            settings.app_name,
            settings.app_version,
            "enabled" if settings.hindsight_enabled else "disabled",
            settings.ollama_model,
        )
        yield
        await dispose_db()

    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID", "X-API-Key"],
        expose_headers=["X-Request-ID", "X-RateLimit-Limit", "Retry-After"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1_000)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(ApiKeyMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    app.include_router(api_router)

    @app.get("/", include_in_schema=False)
    async def root():
        index_file = settings.static_dir / "index.html"
        if index_file.is_file():
            return FileResponse(index_file)
        return {
            "message": f"{settings.app_name} API",
            "version": settings.app_version,
            "docs": "/docs",
            "health": f"{settings.api_prefix}/health",
        }

    _mount_frontend(app)
    return app


app = create_app()

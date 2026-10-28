from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from backend.app.services.errors import OllamaError

pytestmark = pytest.mark.anyio


async def test_root_and_liveness(context):
    root = await context.client.get("/")
    assert root.status_code == 200
    assert root.json()["message"] == "Support AI API"
    assert root.json()["version"] == "1.0.0"
    assert root.json()["docs"] == "/docs"

    live = await context.client.get("/api/health/live")
    assert live.status_code == 200
    assert live.json() == {"status": "alive"}

    ready = await context.client.get("/api/health/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}


async def test_root_serves_built_frontend(context, tmp_path, monkeypatch):
    static_dir = tmp_path / "dist"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html>console</html>", encoding="utf-8")
    monkeypatch.setattr("backend.app.main.settings.static_dir", static_dir)

    response = await context.client.get("/")

    assert response.status_code == 200
    assert "console" in response.text


async def test_health_reports_all_services(context):
    response = await context.client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "status": "ok",
        "service": "Support AI",
        "version": "1.0.0",
        "database": "connected",
        "ollama": "available",
        "hindsight": "available",
        "model": "qwen3:8b",
    }


async def test_health_degrades_when_services_are_down(context):
    context.ollama.healthy = False
    context.hindsight.healthy = False

    response = await context.client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["ollama"] == "unavailable"
    assert payload["hindsight"] == "unavailable"
    assert payload["database"] == "connected"


async def test_health_marks_database_unavailable(context, monkeypatch):
    monkeypatch.setattr(
        context.db,
        "execute",
        AsyncMock(side_effect=RuntimeError("database down")),
    )

    response = await context.client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["database"] == "unavailable"


async def test_readiness_fails_when_database_is_down(context, monkeypatch):
    monkeypatch.setattr(
        context.db,
        "execute",
        AsyncMock(side_effect=RuntimeError("database down")),
    )

    response = await context.client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == "Database is not ready"


async def test_models_endpoint(context):
    response = await context.client.get("/api/models")

    assert response.status_code == 200
    assert response.json() == {
        "models": ["qwen3:8b", "nomic-embed-text"],
        "active_model": "qwen3:8b",
    }

    context.ollama.error = OllamaError("Unable to reach Ollama.")
    failure = await context.client.get("/api/models")
    assert failure.status_code == 503
    assert failure.json()["detail"] == "Unable to reach Ollama."


async def test_request_id_and_security_headers(context):
    response = await context.client.get(
        "/api/health/live",
        headers={"X-Request-ID": "request-123"},
    )

    assert response.headers["X-Request-ID"] == "request-123"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"

    generated = await context.client.get("/api/health/live")
    assert generated.headers["X-Request-ID"]
    assert generated.headers["X-Request-ID"] != "request-123"

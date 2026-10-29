from __future__ import annotations

import pytest

from backend.app.config import settings

pytestmark = pytest.mark.anyio


async def test_api_is_open_when_no_key_is_configured(context):
    response = await context.client.get("/api/customers")
    assert response.status_code == 200


async def test_api_requires_key_when_configured(context, monkeypatch):
    monkeypatch.setattr(settings, "app_api_key", "correct-horse-battery-staple")

    missing = await context.client.get("/api/customers")
    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "ApiKey"
    assert missing.json()["detail"] == "Invalid or missing API key."

    wrong = await context.client.get(
        "/api/customers",
        headers={"X-API-Key": "not-the-key"},
    )
    assert wrong.status_code == 401

    accepted = await context.client.get(
        "/api/customers",
        headers={"X-API-Key": "correct-horse-battery-staple"},
    )
    assert accepted.status_code == 200


async def test_health_probes_stay_public(context, monkeypatch):
    monkeypatch.setattr(settings, "app_api_key", "correct-horse-battery-staple")

    for path in ("/api/health", "/api/health/live", "/api/health/ready"):
        response = await context.client.get(path)
        assert response.status_code == 200, path


async def test_cors_preflight_is_not_blocked(context, monkeypatch):
    monkeypatch.setattr(settings, "app_api_key", "correct-horse-battery-staple")

    response = await context.client.options(
        "/api/chat",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-api-key",
        },
    )

    assert response.status_code == 200


async def test_non_api_paths_are_not_blocked(context, monkeypatch):
    monkeypatch.setattr(settings, "app_api_key", "correct-horse-battery-staple")

    response = await context.client.get("/")
    assert response.status_code == 200

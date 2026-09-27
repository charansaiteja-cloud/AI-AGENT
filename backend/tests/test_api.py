import httpx
import pytest

from backend.app.main import app


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client


@pytest.mark.anyio
async def test_root(client):
    response = await client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "Customer Support Agent API"
    assert data["version"] == "0.2.0"


@pytest.mark.anyio
async def test_health(client):
    response = await client.get("/api/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["service"] == "Customer Support Agent"


@pytest.mark.anyio
async def test_models(client):
    response = await client.get("/api/models")

    assert response.status_code == 200

    data = response.json()

    assert "models" in data
    assert "active_model" in data
    assert data["active_model"] == "qwen3:8b"


@pytest.mark.anyio
async def test_chat_empty_message(client):
    response = await client.post(
        "/api/chat",
        json={"message": ""},
    )

    assert response.status_code == 400

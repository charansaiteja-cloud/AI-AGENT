from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "Customer Support Agent API"
    assert data["version"] == "0.2.0"


def test_health():
    response = client.get("/api/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["service"] == "Customer Support Agent"


def test_models():
    response = client.get("/api/models")

    assert response.status_code == 200

    data = response.json()

    assert "models" in data
    assert "active_model" in data
    assert data["active_model"] == "qwen3:8b"


def test_chat_empty_message():
    response = client.post(
        "/api/chat",
        json={"message": ""},
    )

    assert response.status_code == 400

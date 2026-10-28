from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from backend.app.models.customer import Customer
from backend.app.models.message import Message
from backend.app.services.errors import HindsightError, OllamaError
from backend.app.services.hindsight import MemoryRecord

from .conftest import create_conversation, create_customer

pytestmark = pytest.mark.anyio


async def test_chat_creates_conversation_and_saves_memory(context):
    customer = await create_customer(context.client, "Sarah Chen")
    customer_row = await context.db.get(Customer, customer["id"])
    context.hindsight.memories[customer_row.memory_key] = [
        MemoryRecord(
            id="existing",
            text="Customer prefers concise answers.",
            kind="preference",
        )
    ]
    context.hindsight.recall_records = [
        MemoryRecord(
            id="memory-1",
            text="Customer uses Ubuntu 24.04 on a Dell XPS 15.",
            kind="operating_system",
            source="profile_extraction",
        ),
        MemoryRecord(
            id="memory-2",
            text="Customer prefers concise answers.",
            kind="preference",
        ),
    ]

    response = await context.client.post(
        "/api/chat",
        json={
            "message": "My Wi-Fi keeps disconnecting.",
            "customer_id": customer["id"],
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["response"].startswith("Restart NetworkManager")
    assert payload["model"] == "qwen3:8b"
    assert payload["customer_id"] == customer["id"]
    assert payload["conversation_title"] == "My Wi-Fi keeps disconnecting."
    assert payload["memory_used"] is True
    assert payload["memory_saved"] is True
    assert payload["latency_ms"] >= 0
    assert [item["id"] for item in payload["memories"]] == [
        "memory-1",
        "memory-2",
    ]

    call = context.ollama.calls[0]
    assert call["message"] == "My Wi-Fi keeps disconnecting."
    assert call["history"] == []
    assert "Customer uses Ubuntu 24.04" in call["system_prompt"]
    assert "prefers concise answers" in call["system_prompt"]
    assert "CUSTOMER RESPONSE PREFERENCE" in call["system_prompt"]

    assert context.extractor.calls == ["My Wi-Fi keeps disconnecting."]
    assert context.hindsight.prepare_calls == [customer_row.memory_key]
    retain = context.hindsight.retain_calls[0]
    assert retain["facts"] == context.extractor.facts
    assert retain["existing_texts"] == {"customer prefers concise answers."}
    assert retain["user_text"] == "My Wi-Fi keeps disconnecting."
    assert retain["assistant_text"].startswith("Restart NetworkManager")

    messages = await context.client.get(f"/api/conversations/{payload['conversation_id']}/messages")
    assert messages.status_code == 200
    rows = messages.json()["messages"]
    assert [item["role"] for item in rows] == ["user", "assistant"]
    assert rows[1]["memory_count"] == 2
    assert rows[1]["model"] == "qwen3:8b"


async def test_chat_uses_existing_conversation_and_limits_history(context, monkeypatch):
    customer = await create_customer(context.client, "Sarah Chen")
    conversation = await create_conversation(
        context.client,
        customer["id"],
        "Wi-Fi troubleshooting",
    )
    for index in range(5):
        context.db.add(
            Message(
                conversation_id=conversation["id"],
                role="user" if index % 2 == 0 else "assistant",
                content=f"history-{index}",
            )
        )
    await context.db.commit()

    monkeypatch.setattr(
        "backend.app.api.routes.chat.settings.ollama_history_messages",
        3,
    )

    response = await context.client.post(
        "/api/chat",
        json={
            "message": "What next?",
            "customer_id": customer["id"],
            "conversation_id": conversation["id"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation_id"] == conversation["id"]
    assert payload["conversation_title"] == "Wi-Fi troubleshooting"
    history = context.ollama.calls[0]["history"]
    assert [item["content"] for item in history] == [
        "history-2",
        "history-3",
        "history-4",
    ]


async def test_chat_creates_anonymous_customer_when_no_ids_are_sent(context):
    response = await context.client.post(
        "/api/chat",
        json={"message": "I need help with my account."},
    )

    assert response.status_code == 200
    payload = response.json()
    customer = await context.db.get(Customer, payload["customer_id"])
    assert customer is not None
    assert customer.name == "Anonymous Customer"


async def test_chat_validation_errors(context, monkeypatch):
    blank = await context.client.post(
        "/api/chat",
        json={"message": "   ", "customer_id": 1},
    )
    assert blank.status_code == 400
    assert blank.json()["detail"] == "Message cannot be empty"

    monkeypatch.setattr(
        "backend.app.api.routes.chat.settings.max_message_length",
        10,
    )
    too_long = await context.client.post(
        "/api/chat",
        json={"message": "x" * 11, "customer_id": 1},
    )
    assert too_long.status_code == 400
    assert "Maximum length is 10" in too_long.json()["detail"]

    monkeypatch.setattr(
        "backend.app.api.routes.chat.settings.max_attachments_per_message",
        1,
    )
    too_many = await context.client.post(
        "/api/chat",
        json={
            "message": "See files",
            "customer_id": 1,
            "attachment_ids": [1, 2],
        },
    )
    assert too_many.status_code == 400
    assert "Too many attachments" in too_many.json()["detail"]

    invalid = await context.client.post("/api/chat", json={"message": ""})
    assert invalid.status_code == 422


async def test_chat_rejects_missing_or_mismatched_records(context):
    customer = await create_customer(context.client, "Sarah Chen")
    other = await create_customer(context.client, "Alex Doe")
    conversation = await create_conversation(context.client, customer["id"])

    missing_conversation = await context.client.post(
        "/api/chat",
        json={"message": "Hello", "conversation_id": 999},
    )
    assert missing_conversation.status_code == 404

    mismatch = await context.client.post(
        "/api/chat",
        json={
            "message": "Hello",
            "conversation_id": conversation["id"],
            "customer_id": other["id"],
        },
    )
    assert mismatch.status_code == 400
    assert "does not belong" in mismatch.json()["detail"]

    missing_customer = await context.client.post(
        "/api/chat",
        json={"message": "Hello", "customer_id": 999},
    )
    assert missing_customer.status_code == 404


async def test_chat_links_attachments_and_includes_text_context(context):
    customer = await create_customer(context.client, "Sarah Chen")
    conversation = await create_conversation(context.client, customer["id"])

    upload = await context.client.post(
        f"/api/conversations/{conversation['id']}/attachments",
        files={
            "file": (
                "wifi-log.txt",
                b"NetworkManager disconnected at 10:42.",
                "text/plain",
            )
        },
    )
    attachment = upload.json()

    response = await context.client.post(
        "/api/chat",
        json={
            "message": "What do you see in the log?",
            "customer_id": customer["id"],
            "conversation_id": conversation["id"],
            "attachment_ids": [attachment["id"]],
        },
    )

    assert response.status_code == 200, response.text
    assert "--- Attached file: wifi-log.txt ---" in context.ollama.calls[0]["message"]
    assert "NetworkManager disconnected at 10:42." in context.ollama.calls[0]["message"]

    messages = await context.client.get(f"/api/conversations/{conversation['id']}/messages")
    rows = messages.json()["messages"]
    assert rows[0]["attachments"][0]["id"] == attachment["id"]
    assert rows[0]["attachments"][0]["message_id"] == rows[0]["id"]


async def test_chat_rejects_attachments_from_another_conversation(context):
    customer = await create_customer(context.client, "Sarah Chen")
    first = await create_conversation(context.client, customer["id"])
    second = await create_conversation(context.client, customer["id"])

    upload = await context.client.post(
        f"/api/conversations/{first['id']}/attachments",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    attachment = upload.json()

    response = await context.client.post(
        "/api/chat",
        json={
            "message": "Check this",
            "customer_id": customer["id"],
            "conversation_id": second["id"],
            "attachment_ids": [attachment["id"]],
        },
    )

    assert response.status_code == 400
    assert "not part of this conversation" in response.json()["detail"]


async def test_chat_rejects_already_linked_attachments(context):
    customer = await create_customer(context.client, "Sarah Chen")
    conversation = await create_conversation(context.client, customer["id"])
    upload = await context.client.post(
        f"/api/conversations/{conversation['id']}/attachments",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    attachment = upload.json()

    first = await context.client.post(
        "/api/chat",
        json={
            "message": "First use",
            "customer_id": customer["id"],
            "conversation_id": conversation["id"],
            "attachment_ids": [attachment["id"]],
        },
    )
    assert first.status_code == 200

    second = await context.client.post(
        "/api/chat",
        json={
            "message": "Second use",
            "customer_id": customer["id"],
            "conversation_id": conversation["id"],
            "attachment_ids": [attachment["id"]],
        },
    )
    assert second.status_code == 400
    assert "already linked" in second.json()["detail"]


async def test_chat_returns_503_when_model_is_unavailable(context):
    customer = await create_customer(context.client, "Sarah Chen")
    conversation = await create_conversation(context.client, customer["id"])
    context.ollama.error = OllamaError("down")

    response = await context.client.post(
        "/api/chat",
        json={
            "message": "Hello",
            "customer_id": customer["id"],
            "conversation_id": conversation["id"],
        },
    )

    assert response.status_code == 503
    assert "language model is unavailable" in response.json()["detail"]
    messages = await context.client.get(f"/api/conversations/{conversation['id']}/messages")
    assert messages.json()["messages"] == []


async def test_chat_returns_500_on_unexpected_model_failure(context):
    customer = await create_customer(context.client, "Sarah Chen")
    context.ollama.error = RuntimeError("boom")

    response = await context.client.post(
        "/api/chat",
        json={"message": "Hello", "customer_id": customer["id"]},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "The response could not be generated."


async def test_chat_returns_500_when_persistence_fails(context, monkeypatch):
    customer = await create_customer(context.client, "Sarah Chen")
    monkeypatch.setattr(
        context.db,
        "commit",
        AsyncMock(side_effect=RuntimeError("database down")),
    )

    transport = httpx.ASGITransport(
        app=context.app,
        raise_app_exceptions=False,
    )
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/chat",
            json={"message": "Hello", "customer_id": customer["id"]},
        )

    assert response.status_code == 500
    assert response.json()["detail"] == "The conversation could not be saved."


async def test_chat_survives_memory_failures(context):
    customer = await create_customer(context.client, "Sarah Chen")

    context.hindsight.fail_recall = HindsightError("recall down")
    recall_failure = await context.client.post(
        "/api/chat",
        json={"message": "Hello", "customer_id": customer["id"]},
    )
    assert recall_failure.status_code == 200
    assert recall_failure.json()["memory_used"] is False

    context.hindsight.fail_recall = None
    context.extractor.error = RuntimeError("extractor down")
    extraction_failure = await context.client.post(
        "/api/chat",
        json={"message": "Hello again", "customer_id": customer["id"]},
    )
    assert extraction_failure.status_code == 200
    assert extraction_failure.json()["memory_saved"] is True
    assert context.hindsight.retain_calls[-1]["facts"] == []

    context.extractor.error = None
    context.hindsight.fail_retain = HindsightError("retain down")
    retain_failure = await context.client.post(
        "/api/chat",
        json={"message": "One more", "customer_id": customer["id"]},
    )
    assert retain_failure.status_code == 200
    assert retain_failure.json()["memory_saved"] is False


async def test_chat_truncates_long_titles(context):
    customer = await create_customer(context.client, "Sarah Chen")
    message = "word " * 20

    response = await context.client.post(
        "/api/chat",
        json={"message": message, "customer_id": customer["id"]},
    )

    assert response.status_code == 200
    title = response.json()["conversation_title"]
    assert len(title) <= 60
    assert title.endswith("...")


async def test_chat_passes_recalled_memory_into_prompt(context):
    customer = await create_customer(context.client, "Sarah Chen")
    context.hindsight.recall_records = [
        MemoryRecord(
            id="memory-1",
            text="Customer's device is a Dell XPS 15.",
            kind="product",
        )
    ]

    response = await context.client.post(
        "/api/chat",
        json={"message": "The issue is back.", "customer_id": customer["id"]},
    )

    assert response.status_code == 200
    assert "Dell XPS 15" in context.ollama.calls[0]["system_prompt"]
    assert "CUSTOMER RESPONSE PREFERENCE" not in context.ollama.calls[0]["system_prompt"]

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.app.models.attachment import Attachment
from backend.app.models.conversation import Conversation
from backend.app.models.customer import Customer
from backend.app.models.message import Message
from backend.app.services.errors import HindsightError
from backend.app.services.hindsight import MemoryRecord

from .conftest import create_conversation, create_customer

pytestmark = pytest.mark.anyio


async def test_list_customers_empty(context):
    response = await context.client.get("/api/customers")

    assert response.status_code == 200
    assert response.json() == []


async def test_customer_crud_and_duplicate_email(context):
    sarah = await create_customer(context.client, "Sarah Chen", "sarah@acme.example")

    assert sarah["name"] == "Sarah Chen"
    assert sarah["email"] == "sarah@acme.example"
    assert sarah["conversation_count"] == 0
    assert sarah["last_activity_at"] is None

    fetched = await context.client.get(f"/api/customers/{sarah['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == sarah["id"]

    updated = await context.client.patch(
        f"/api/customers/{sarah['id']}",
        json={"name": "Sarah C.", "email": "sarah.c@acme.example"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Sarah C."
    assert updated.json()["email"] == "sarah.c@acme.example"

    duplicate = await context.client.post(
        "/api/customers",
        json={"name": "Another Sarah", "email": "SARAH.C@acme.example"},
    )
    assert duplicate.status_code == 409
    assert "already exists" in duplicate.json()["detail"]

    other = await create_customer(context.client, "Alex Doe", "alex@example.com")
    conflict = await context.client.patch(
        f"/api/customers/{other['id']}",
        json={"email": "sarah.c@acme.example"},
    )
    assert conflict.status_code == 409

    listing = await context.client.get("/api/customers")
    assert listing.status_code == 200
    assert {item["id"] for item in listing.json()} == {sarah["id"], other["id"]}


async def test_customer_validation_and_missing_records(context):
    blank = await context.client.post("/api/customers", json={"name": "   "})
    assert blank.status_code == 422

    bad_email = await context.client.post(
        "/api/customers",
        json={"name": "Sarah", "email": "not-an-email"},
    )
    assert bad_email.status_code == 422

    missing = await context.client.get("/api/customers/999")
    assert missing.status_code == 404

    missing_update = await context.client.patch(
        "/api/customers/999",
        json={"name": "Nobody"},
    )
    assert missing_update.status_code == 404


async def test_customer_stats_follow_conversations(context):
    customer = await create_customer(context.client, "Sarah Chen")
    conversation = await create_conversation(
        context.client,
        customer["id"],
        "Wi-Fi issue",
    )

    fetched = await context.client.get(f"/api/customers/{customer['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["conversation_count"] == 1
    assert fetched.json()["last_activity_at"] is not None

    listing = await context.client.get("/api/customers")
    assert listing.json()[0]["id"] == customer["id"]
    assert listing.json()[0]["conversation_count"] == 1
    assert listing.json()[0]["last_activity_at"] is not None

    assert conversation["title"] == "Wi-Fi issue"


async def test_delete_customer_erases_bank_files_and_rows(context):
    customer = await create_customer(context.client, "Sarah Chen")
    conversation = await create_conversation(context.client, customer["id"])
    customer_row = await context.db.get(Customer, customer["id"])

    message = Message(
        conversation_id=conversation["id"],
        role="user",
        content="Hello",
    )
    context.db.add(message)
    await context.db.flush()

    directory = context.upload_dir / str(conversation["id"])
    directory.mkdir(parents=True)
    stored_file = directory / "stored.txt"
    stored_file.write_text("attachment", encoding="utf-8")

    attachment = Attachment(
        conversation_id=conversation["id"],
        message_id=message.id,
        original_filename="notes.txt",
        stored_filename="stored.txt",
        content_type="text/plain",
        file_size=10,
    )
    context.db.add(attachment)
    await context.db.commit()

    response = await context.client.delete(f"/api/customers/{customer['id']}")

    assert response.status_code == 204
    assert context.hindsight.delete_calls == [customer_row.memory_key]
    assert not stored_file.exists()
    assert await context.db.get(Customer, customer["id"]) is None
    assert await context.db.get(Conversation, conversation["id"]) is None


async def test_delete_customer_is_blocked_when_bank_cannot_be_erased(context):
    customer = await create_customer(context.client, "Sarah Chen")
    context.hindsight.fail_delete = HindsightError("unavailable")

    response = await context.client.delete(f"/api/customers/{customer['id']}")

    assert response.status_code == 502
    assert "memory bank could not be erased" in response.json()["detail"]
    assert await context.db.get(Customer, customer["id"]) is not None


async def test_list_conversations_includes_message_summary(context):
    customer = await create_customer(context.client, "Sarah Chen")
    conversation = await create_conversation(context.client, customer["id"])

    first = Message(
        conversation_id=conversation["id"],
        role="user",
        content="My Wi-Fi keeps dropping.",
    )
    second = Message(
        conversation_id=conversation["id"],
        role="assistant",
        content="Let's restart the network manager.",
        model="qwen3:8b",
    )
    context.db.add_all([first, second])
    await context.db.commit()

    response = await context.client.get(f"/api/customers/{customer['id']}/conversations")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == conversation["id"]
    assert payload[0]["message_count"] == 2
    assert payload[0]["last_message"] == "Let's restart the network manager."
    assert payload[0]["last_message_at"] is not None

    missing = await context.client.get("/api/customers/999/conversations")
    assert missing.status_code == 404


async def test_create_conversation_titles_and_missing_customer(context):
    customer = await create_customer(context.client, "Sarah Chen")

    default = await create_conversation(context.client, customer["id"])
    assert default["title"] == "New conversation"

    titled = await create_conversation(
        context.client,
        customer["id"],
        "  Wi-Fi drops  ",
    )
    assert titled["title"] == "Wi-Fi drops"

    blank = await create_conversation(context.client, customer["id"], "   ")
    assert blank["title"] == "New conversation"

    missing = await context.client.post(
        "/api/customers/999/conversations",
        json={},
    )
    assert missing.status_code == 404


async def test_memories_endpoint_reports_disabled_and_unavailable(context, monkeypatch):
    customer = await create_customer(context.client, "Sarah Chen")
    customer_row = await context.db.get(Customer, customer["id"])

    monkeypatch.setattr("backend.app.api.routes.customers.settings.hindsight_enabled", False)
    disabled = await context.client.get(f"/api/customers/{customer['id']}/memories")
    assert disabled.status_code == 200
    assert disabled.json()["available"] is False
    assert disabled.json()["error"] == "Long-term memory is disabled."

    monkeypatch.setattr("backend.app.api.routes.customers.settings.hindsight_enabled", True)
    context.hindsight.fail_list = HindsightError("offline")
    unavailable = await context.client.get(f"/api/customers/{customer['id']}/memories")
    assert unavailable.status_code == 200
    assert unavailable.json()["available"] is False
    assert unavailable.json()["error"] == "The memory service is unavailable."
    assert customer_row.memory_key not in {call[0] for call in context.hindsight.list_calls}


async def test_memories_endpoint_returns_records(context):
    customer = await create_customer(context.client, "Sarah Chen")
    customer_row = await context.db.get(Customer, customer["id"])
    context.hindsight.memories[customer_row.memory_key] = [
        MemoryRecord(
            id="memory-1",
            text="Customer prefers concise answers.",
            kind="preference",
            source="profile_extraction",
            context="customer profile fact",
            created_at=datetime(2026, 10, 28, 12, 0, tzinfo=UTC),
            score=0.91,
        )
    ]

    response = await context.client.get(f"/api/customers/{customer['id']}/memories")

    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["count"] == 1
    assert payload["memories"][0]["id"] == "memory-1"
    assert payload["memories"][0]["kind"] == "preference"
    assert payload["memories"][0]["score"] == 0.91

    missing = await context.client.get("/api/customers/999/memories")
    assert missing.status_code == 404


async def test_clear_memories_success_disabled_and_failure(context, monkeypatch):
    customer = await create_customer(context.client, "Sarah Chen")
    customer_row = await context.db.get(Customer, customer["id"])

    cleared = await context.client.delete(f"/api/customers/{customer['id']}/memories")
    assert cleared.status_code == 204
    assert context.hindsight.delete_calls == [customer_row.memory_key]

    context.hindsight.fail_delete = HindsightError("offline")
    failed = await context.client.delete(f"/api/customers/{customer['id']}/memories")
    assert failed.status_code == 503
    assert failed.json()["detail"] == "The memory service is unavailable."

    monkeypatch.setattr("backend.app.api.routes.customers.settings.hindsight_enabled", False)
    disabled = await context.client.delete(f"/api/customers/{customer['id']}/memories")
    assert disabled.status_code == 503
    assert disabled.json()["detail"] == "Long-term memory is disabled."

    missing = await context.client.delete("/api/customers/999/memories")
    assert missing.status_code == 404

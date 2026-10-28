from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from backend.app.models.attachment import Attachment
from backend.app.models.conversation import Conversation
from backend.app.models.message import Message

from .conftest import create_conversation, create_customer

pytestmark = pytest.mark.anyio


async def test_get_and_update_conversation(context):
    customer = await create_customer(context.client, "Sarah Chen")
    conversation = await create_conversation(context.client, customer["id"])

    fetched = await context.client.get(f"/api/conversations/{conversation['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == conversation["id"]

    updated = await context.client.patch(
        f"/api/conversations/{conversation['id']}",
        json={"title": "Resolved Wi-Fi", "status": "archived"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Resolved Wi-Fi"
    assert updated.json()["status"] == "archived"

    invalid = await context.client.patch(
        f"/api/conversations/{conversation['id']}",
        json={"status": "closed"},
    )
    assert invalid.status_code == 422

    missing = await context.client.get("/api/conversations/999")
    assert missing.status_code == 404

    missing_update = await context.client.patch(
        "/api/conversations/999",
        json={"title": "Nope"},
    )
    assert missing_update.status_code == 404


async def test_delete_conversation_removes_messages_attachments_and_files(context):
    customer = await create_customer(context.client, "Sarah Chen")
    conversation = await create_conversation(context.client, customer["id"])

    message = Message(
        conversation_id=conversation["id"],
        role="user",
        content="Hello",
    )
    context.db.add(message)
    await context.db.flush()

    directory = context.upload_dir / str(conversation["id"])
    directory.mkdir(parents=True)
    stored = directory / "stored.txt"
    stored.write_text("data", encoding="utf-8")

    context.db.add(
        Attachment(
            conversation_id=conversation["id"],
            message_id=message.id,
            original_filename="notes.txt",
            stored_filename="stored.txt",
            content_type="text/plain",
            file_size=4,
        )
    )
    await context.db.commit()

    response = await context.client.delete(f"/api/conversations/{conversation['id']}")

    assert response.status_code == 204
    assert not directory.exists()
    assert await context.db.get(Conversation, conversation["id"]) is None
    assert await context.db.get(Message, message.id) is None

    missing = await context.client.delete("/api/conversations/999")
    assert missing.status_code == 404


async def test_get_messages_groups_linked_attachments(context):
    customer = await create_customer(context.client, "Sarah Chen")
    conversation = await create_conversation(context.client, customer["id"])

    message = Message(
        conversation_id=conversation["id"],
        role="user",
        content="See the log.",
    )
    context.db.add(message)
    await context.db.flush()

    linked = Attachment(
        conversation_id=conversation["id"],
        message_id=message.id,
        original_filename="wifi.log",
        stored_filename="linked.txt",
        content_type="text/plain",
        file_size=12,
    )
    unlinked = Attachment(
        conversation_id=conversation["id"],
        original_filename="draft.txt",
        stored_filename="unlinked.txt",
        content_type="text/plain",
        file_size=5,
    )
    context.db.add_all([linked, unlinked])
    await context.db.commit()

    response = await context.client.get(f"/api/conversations/{conversation['id']}/messages")

    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation_id"] == conversation["id"]
    assert len(payload["messages"]) == 1
    assert payload["messages"][0]["content"] == "See the log."
    assert len(payload["messages"][0]["attachments"]) == 1
    assert payload["messages"][0]["attachments"][0]["original_filename"] == "wifi.log"

    missing = await context.client.get("/api/conversations/999/messages")
    assert missing.status_code == 404


async def test_upload_list_and_delete_attachment(context):
    customer = await create_customer(context.client, "Sarah Chen")
    conversation = await create_conversation(context.client, customer["id"])

    upload = await context.client.post(
        f"/api/conversations/{conversation['id']}/attachments",
        files={"file": ("notes.txt", b"hello attachment", "text/plain")},
    )

    assert upload.status_code == 201, upload.text
    payload = upload.json()
    assert payload["original_filename"] == "notes.txt"
    assert payload["content_type"] == "text/plain"
    assert payload["file_size"] == 16
    assert payload["download_url"] == f"/api/attachments/{payload['id']}"

    listing = await context.client.get(f"/api/conversations/{conversation['id']}/attachments")
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [payload["id"]]

    downloaded = await context.client.get(payload["download_url"])
    assert downloaded.status_code == 200
    assert downloaded.content == b"hello attachment"
    assert "attachment" in downloaded.headers["content-disposition"]

    deleted = await context.client.delete(f"/api/attachments/{payload['id']}")
    assert deleted.status_code == 204
    assert await context.db.get(Attachment, payload["id"]) is None

    missing = await context.client.get(f"/api/conversations/{conversation['id']}/attachments")
    assert missing.status_code == 200
    assert missing.json() == []


async def test_upload_validation_errors(context, monkeypatch):
    customer = await create_customer(context.client, "Sarah Chen")
    conversation = await create_conversation(context.client, customer["id"])
    endpoint = f"/api/conversations/{conversation['id']}/attachments"

    unsupported = await context.client.post(
        endpoint,
        files={"file": ("malware.exe", b"data", "application/octet-stream")},
    )
    assert unsupported.status_code == 415

    empty = await context.client.post(
        endpoint,
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert empty.status_code == 400

    mismatch = await context.client.post(
        endpoint,
        files={"file": ("photo.png", b"data", "text/plain")},
    )
    assert mismatch.status_code == 415

    monkeypatch.setattr(
        "backend.app.services.attachments.settings.max_upload_size",
        4,
    )
    oversized = await context.client.post(
        endpoint,
        files={"file": ("large.txt", b"12345", "text/plain")},
    )
    assert oversized.status_code == 413

    missing = await context.client.post(
        "/api/conversations/999/attachments",
        files={"file": ("notes.txt", b"data", "text/plain")},
    )
    assert missing.status_code == 404


async def test_upload_rolls_back_file_when_database_commit_fails(context, monkeypatch):
    customer = await create_customer(context.client, "Sarah Chen")
    conversation = await create_conversation(context.client, customer["id"])
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
            f"/api/conversations/{conversation['id']}/attachments",
            files={"file": ("notes.txt", b"data", "text/plain")},
        )

    assert response.status_code == 500
    directory = context.upload_dir / str(conversation["id"])
    assert not directory.exists() or not any(directory.iterdir())


async def test_download_attachment_inline_missing_file_and_missing_record(context):
    customer = await create_customer(context.client, "Sarah Chen")
    conversation = await create_conversation(context.client, customer["id"])

    directory = context.upload_dir / str(conversation["id"])
    directory.mkdir(parents=True)
    image_file = directory / "photo.png"
    image_file.write_bytes(b"png-bytes")

    image = Attachment(
        conversation_id=conversation["id"],
        original_filename="photo.png",
        stored_filename="photo.png",
        content_type="image/png",
        file_size=9,
    )
    missing_file = Attachment(
        conversation_id=conversation["id"],
        original_filename="gone.txt",
        stored_filename="gone.txt",
        content_type="text/plain",
        file_size=4,
    )
    context.db.add_all([image, missing_file])
    await context.db.commit()

    inline = await context.client.get(f"/api/attachments/{image.id}?inline=true")
    assert inline.status_code == 200
    assert inline.headers["content-disposition"].startswith("inline")

    not_found_file = await context.client.get(f"/api/attachments/{missing_file.id}")
    assert not_found_file.status_code == 404
    assert not_found_file.json()["detail"] == "Attachment file not found"

    missing_record = await context.client.get("/api/attachments/999")
    assert missing_record.status_code == 404
    assert missing_record.json()["detail"] == "Attachment not found"

    missing_delete = await context.client.delete("/api/attachments/999")
    assert missing_delete.status_code == 404

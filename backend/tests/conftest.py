from __future__ import annotations

from collections import defaultdict
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import backend.app.models  # noqa: F401 - registers every table
from backend.app.api.deps import (
    get_attachment_service,
    get_hindsight,
    get_memory_extractor,
    get_ollama,
)
from backend.app.config import settings
from backend.app.db.database import Base, get_db
from backend.app.main import create_app
from backend.app.services.attachments import AttachmentService
from backend.app.services.memory import ExtractedFact


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class FakeOllama:
    def __init__(self) -> None:
        self.response = "Restart NetworkManager, then reconnect to the network."
        self.error: Exception | None = None
        self.calls: list[dict] = []
        self.json_data: dict = {
            "facts": [
                {
                    "kind": "issue",
                    "text": "Customer reports that Wi-Fi keeps disconnecting.",
                }
            ]
        }
        self.json_error: Exception | None = None
        self.healthy = True
        self.models = ["qwen3:8b", "nomic-embed-text"]

    async def chat(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> str:
        self.calls.append(
            {
                "message": message,
                "history": history or [],
                "system_prompt": system_prompt,
                **kwargs,
            }
        )
        if self.error is not None:
            raise self.error
        return self.response

    async def chat_json(self, prompt: str, num_predict: int = 400) -> dict:
        if self.json_error is not None:
            raise self.json_error
        return self.json_data

    async def health_check(self) -> bool:
        return self.healthy

    async def list_models(self) -> list[str]:
        if self.error is not None:
            raise self.error
        return self.models


class FakeHindsight:
    def __init__(self) -> None:
        self.memories: dict[str, list] = defaultdict(list)
        self.recall_records: list = []
        self.retain_calls: list[dict] = []
        self.prepare_calls: list[str] = []
        self.list_calls: list[tuple[str, int]] = []
        self.delete_calls: list[str] = []
        self.healthy = True
        self.fail_recall: Exception | None = None
        self.fail_retain: Exception | None = None
        self.fail_list: Exception | None = None
        self.fail_delete: Exception | None = None
        self.retain_result = True

    async def health_check(self) -> bool:
        return self.healthy

    async def recall(
        self,
        memory_key: str,
        query: str,
        limit: int | None = None,
    ) -> list:
        if self.fail_recall is not None:
            raise self.fail_recall
        return self.recall_records[: limit or len(self.recall_records)]

    async def retain_turn(
        self,
        memory_key: str,
        conversation_id: int,
        user_text: str,
        assistant_text: str,
        facts: list[ExtractedFact] | None = None,
        existing_texts: set[str] | None = None,
    ) -> bool:
        if self.fail_retain is not None:
            raise self.fail_retain
        self.retain_calls.append(
            {
                "memory_key": memory_key,
                "conversation_id": conversation_id,
                "user_text": user_text,
                "assistant_text": assistant_text,
                "facts": facts,
                "existing_texts": existing_texts,
            }
        )
        return self.retain_result

    async def prepare_retain(
        self,
        memory_key: str,
        limit: int = 200,
    ) -> set[str]:
        self.prepare_calls.append(memory_key)
        if self.fail_list is not None:
            return set()
        return {record.text.casefold() for record in self.memories[memory_key][:limit]}

    async def list_memories(self, memory_key: str, limit: int = 100) -> list:
        if self.fail_list is not None:
            raise self.fail_list
        self.list_calls.append((memory_key, limit))
        return self.memories[memory_key][:limit]

    async def delete_bank(self, memory_key: str) -> bool:
        if self.fail_delete is not None:
            raise self.fail_delete
        self.delete_calls.append(memory_key)
        self.memories.pop(memory_key, None)
        return True


class FakeExtractor:
    def __init__(self) -> None:
        self.facts = [
            ExtractedFact(
                kind="issue",
                text="Customer reports that Wi-Fi keeps disconnecting.",
            )
        ]
        self.error: Exception | None = None
        self.calls: list[str] = []

    async def extract(self, message: str) -> list[ExtractedFact]:
        self.calls.append(message)
        if self.error is not None:
            raise self.error
        return self.facts


@pytest.fixture
async def context(tmp_path, monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        autoflush=False,
    )
    session = session_factory()

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    attachment_service = AttachmentService(upload_dir=upload_dir)

    ollama = FakeOllama()
    hindsight = FakeHindsight()
    extractor = FakeExtractor()

    monkeypatch.setattr(settings, "hindsight_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    monkeypatch.setattr(settings, "environment", "test")
    monkeypatch.setattr(settings, "upload_dir", upload_dir)
    monkeypatch.setattr(settings, "static_dir", tmp_path / "no-static-build")
    monkeypatch.setattr(settings, "max_message_length", 4_000)
    monkeypatch.setattr(settings, "max_attachments_per_message", 5)

    app = create_app()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_ollama] = lambda: ollama
    app.dependency_overrides[get_hindsight] = lambda: hindsight
    app.dependency_overrides[get_memory_extractor] = lambda: extractor
    app.dependency_overrides[get_attachment_service] = lambda: attachment_service

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield SimpleNamespace(
            app=app,
            client=client,
            db=session,
            ollama=ollama,
            hindsight=hindsight,
            extractor=extractor,
            attachments=attachment_service,
            upload_dir=upload_dir,
        )

    await session.close()
    await engine.dispose()


async def create_customer(client, name: str = "Sarah Chen", email=None) -> dict:
    response = await client.post(
        "/api/customers",
        json={"name": name, "email": email},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_conversation(client, customer_id: int, title=None) -> dict:
    payload = {"title": title} if title is not None else {}
    response = await client.post(
        f"/api/customers/{customer_id}/conversations",
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()

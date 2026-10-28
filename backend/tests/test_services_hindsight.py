from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
import respx

from backend.app.services.errors import HindsightError
from backend.app.services.hindsight import (
    HindsightClient,
    MemoryRecord,
    _parse_datetime,
    _score,
)
from backend.app.services.memory import ExtractedFact

pytestmark = pytest.mark.anyio

BASE = "http://hindsight.test"
BANK = f"{BASE}/v1/default/banks/bank-abc"


def client(**overrides) -> HindsightClient:
    options = {
        "base_url": BASE,
        "bank_prefix": "bank",
        "timeout_seconds": 2,
        "enabled": True,
    }
    options.update(overrides)
    return HindsightClient(**options)


def test_bank_id_and_parse_helpers():
    service = client()
    assert service.bank_id("abc") == "bank-abc"
    assert _parse_datetime(None) is None
    assert _parse_datetime(123) is None
    assert _parse_datetime("not-a-date") is None
    assert _parse_datetime("2026-10-28T12:00:00Z") == datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
    assert _parse_datetime("2026-10-28T12:00:00") == datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
    assert _score(None) is None
    assert _score("0.5") is None
    assert _score({"final": 0.75}) == 0.75
    assert _score({"final": 1}) == 1.0
    assert _score({"final": "high"}) is None


@respx.mock
async def test_health_check():
    route = respx.get(f"{BASE}/health").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )
    assert await client().health_check() is True
    assert route.called
    respx.reset()

    respx.get(f"{BASE}/health").mock(return_value=httpx.Response(500))
    assert await client().health_check() is False
    respx.reset()

    assert await client(enabled=False).health_check() is False


@respx.mock
async def test_ensure_bank_patch_and_cache():
    patch = respx.patch(BANK).mock(return_value=httpx.Response(200))
    service = client()

    assert await service.ensure_bank("abc") == "bank-abc"
    assert await service.ensure_bank("abc") == "bank-abc"
    assert patch.call_count == 1

    payload = patch.calls[0].request.content
    assert b"retain_extraction_mode" in payload
    assert b"chunks" in payload
    assert b"enable_observations" in payload


@respx.mock
async def test_ensure_bank_falls_back_to_put():
    respx.patch(BANK).mock(return_value=httpx.Response(404))
    put = respx.put(BANK).mock(return_value=httpx.Response(200))

    assert await client().ensure_bank("abc") == "bank-abc"
    assert put.called


@respx.mock
async def test_ensure_bank_errors():
    respx.patch(BANK).mock(return_value=httpx.Response(500))
    with pytest.raises(HindsightError, match="create a customer bank"):
        await client().ensure_bank("abc")
    respx.reset()

    respx.patch(BANK).mock(return_value=httpx.Response(404))
    respx.put(BANK).mock(return_value=httpx.Response(500))
    with pytest.raises(HindsightError, match="create a customer bank"):
        await client().ensure_bank("abc")


@respx.mock
async def test_prepare_retain_warm_bank_and_loads_texts():
    respx.patch(BANK).mock(return_value=httpx.Response(200))
    respx.get(f"{BANK}/memories/list").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {"id": "1", "text": "Customer prefers concise answers."},
                    {"id": "2", "text": "Customer uses Ubuntu."},
                ]
            },
        )
    )

    texts = await client().prepare_retain("abc")

    assert texts == {
        "customer prefers concise answers.",
        "customer uses ubuntu.",
    }


@respx.mock
async def test_prepare_retain_tolerates_list_failure():
    respx.patch(BANK).mock(return_value=httpx.Response(200))
    respx.get(f"{BANK}/memories/list").mock(return_value=httpx.Response(500))

    assert await client().prepare_retain("abc") == set()


async def test_prepare_retain_disabled():
    assert await client(enabled=False).prepare_retain("abc") == set()


@respx.mock
async def test_retain_turn_with_facts_and_deduplication():
    respx.patch(BANK).mock(return_value=httpx.Response(200))
    respx.get(f"{BANK}/memories/list").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "1",
                        "text": "Customer reports that Wi-Fi drops.",
                    }
                ]
            },
        )
    )
    post = respx.post(f"{BANK}/memories").mock(return_value=httpx.Response(200, json={"items": []}))

    saved = await client().retain_turn(
        "abc",
        7,
        "My Wi-Fi drops.",
        "Restart the network manager.",
        [
            ExtractedFact(
                kind="issue",
                text="Customer reports that Wi-Fi drops.",
            ),
            ExtractedFact(
                kind="operating_system",
                text="Customer uses Ubuntu 24.04.",
            ),
        ],
    )

    assert saved is True
    import json

    payload = json.loads(post.calls[0].request.content)
    assert payload["async"] is False
    contents = [item["content"] for item in payload["items"]]
    assert contents[0] == "Customer uses Ubuntu 24.04."
    assert contents[1].startswith("Support interaction.")
    assert "My Wi-Fi drops." in contents[1]
    assert payload["items"][0]["metadata"] == {
        "kind": "operating_system",
        "source": "profile_extraction",
    }
    assert payload["items"][0]["document_id"] == "conversation-7"


@respx.mock
async def test_retain_turn_uses_prefetched_texts_without_list_call():
    respx.patch(BANK).mock(return_value=httpx.Response(200))
    post = respx.post(f"{BANK}/memories").mock(return_value=httpx.Response(200))
    list_route = respx.get(f"{BANK}/memories/list")

    saved = await client().retain_turn(
        "abc",
        8,
        "Hello",
        "Hi",
        [ExtractedFact(kind="other", text="Customer says hello.")],
        existing_texts={"customer says hello."},
    )

    assert saved is True
    assert not list_route.called
    import json

    payload = json.loads(post.calls[0].request.content)
    assert len(payload["items"]) == 1
    assert payload["items"][0]["metadata"]["kind"] == "interaction"


@respx.mock
async def test_retain_turn_tolerates_list_failure_and_handles_post_failure():
    respx.patch(BANK).mock(return_value=httpx.Response(200))
    respx.get(f"{BANK}/memories/list").mock(return_value=httpx.Response(500))
    respx.post(f"{BANK}/memories").mock(return_value=httpx.Response(200))

    assert await client().retain_turn("abc", 1, "Hello", "Hi") is True
    respx.reset()

    respx.patch(BANK).mock(return_value=httpx.Response(200))
    respx.get(f"{BANK}/memories/list").mock(return_value=httpx.Response(200))
    respx.post(f"{BANK}/memories").mock(return_value=httpx.Response(500))
    with pytest.raises(HindsightError, match="retain this conversation"):
        await client().retain_turn("abc", 1, "Hello", "Hi")


async def test_retain_turn_disabled():
    assert await client(enabled=False).retain_turn("abc", 1, "Hello", "Hi") is False


@respx.mock
async def test_recall_parses_and_deduplicates_results():
    route = respx.post(f"{BANK}/memories/recall").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "1",
                        "text": "Customer uses Ubuntu 24.04.",
                        "context": "profile",
                        "mentioned_at": "2026-10-28T12:00:00Z",
                        "metadata": {
                            "kind": "operating_system",
                            "source": "profile_extraction",
                        },
                        "scores": {"final": 0.88},
                    },
                    {
                        "id": "2",
                        "text": "Customer uses Ubuntu 24.04.",
                    },
                    {
                        "id": "3",
                        "text": "   ",
                    },
                    "not-a-dict",
                    {
                        "id": "4",
                        "text": "Customer prefers concise answers.",
                        "metadata": "bad",
                        "scores": "bad",
                        "occurred_start": "2026-10-27T09:30:00",
                    },
                ]
            },
        )
    )

    records = await client().recall("abc", "What do I know?", limit=2)

    assert len(records) == 2
    assert records[0] == MemoryRecord(
        id="1",
        text="Customer uses Ubuntu 24.04.",
        kind="operating_system",
        source="profile_extraction",
        context="profile",
        created_at=datetime(2026, 10, 28, 12, 0, tzinfo=UTC),
        score=0.88,
    )
    assert records[1].kind == "other"
    assert records[1].source == "memory"
    assert records[1].created_at == datetime(2026, 10, 27, 9, 30, tzinfo=UTC)
    assert records[1].score is None
    payload = route.calls[0].request.content
    assert b"max_tokens" in payload
    assert b"prefer_observations" in payload


@respx.mock
async def test_recall_returns_empty_on_missing_bank_and_errors_on_failure():
    respx.post(f"{BANK}/memories/recall").mock(return_value=httpx.Response(404))
    assert await client().recall("abc", "query") == []
    respx.reset()

    respx.post(f"{BANK}/memories/recall").mock(return_value=httpx.Response(500))
    with pytest.raises(HindsightError, match="recall customer context"):
        await client().recall("abc", "query")


async def test_recall_disabled():
    assert await client(enabled=False).recall("abc", "query") == []


@respx.mock
async def test_list_memories_parses_and_deduplicates():
    route = respx.get(f"{BANK}/memories/list").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "1",
                        "text": "Customer uses Ubuntu.",
                        "date": "2026-10-28T12:00:00Z",
                        "metadata": {"kind": "operating_system"},
                    },
                    {"id": "2", "text": "Customer uses Ubuntu."},
                    {"id": "3", "text": ""},
                    "bad",
                    {
                        "id": "4",
                        "text": "Customer prefers short replies.",
                        "metadata": "bad",
                    },
                ]
            },
        )
    )

    records = await client().list_memories("abc", limit=50)

    assert len(records) == 2
    assert records[0].text == "Customer uses Ubuntu."
    assert records[0].kind == "operating_system"
    assert records[0].created_at == datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
    assert records[1].kind == "other"
    assert route.calls[0].request.url.params["limit"] == "50"


@respx.mock
async def test_list_memories_returns_empty_on_missing_bank_and_errors():
    respx.get(f"{BANK}/memories/list").mock(return_value=httpx.Response(404))
    assert await client().list_memories("abc") == []
    respx.reset()

    respx.get(f"{BANK}/memories/list").mock(return_value=httpx.Response(500))
    with pytest.raises(HindsightError, match="list customer memories"):
        await client().list_memories("abc")


async def test_list_memories_disabled():
    assert await client(enabled=False).list_memories("abc") == []


@respx.mock
async def test_delete_bank_success_and_missing_bank():
    service = client()
    service._ensured_banks.add("bank-abc")
    route = respx.delete(BANK).mock(return_value=httpx.Response(200))

    assert await service.delete_bank("abc") is True
    assert route.called
    assert "bank-abc" not in service._ensured_banks
    respx.reset()

    service._ensured_banks.add("bank-abc")
    respx.delete(BANK).mock(return_value=httpx.Response(404))
    assert await service.delete_bank("abc") is True
    assert "bank-abc" not in service._ensured_banks


@respx.mock
async def test_delete_bank_failure():
    respx.delete(BANK).mock(return_value=httpx.Response(500))
    with pytest.raises(HindsightError, match="delete this customer's bank"):
        await client().delete_bank("abc")


async def test_delete_bank_disabled():
    assert await client(enabled=False).delete_bank("abc") is False

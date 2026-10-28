from __future__ import annotations

import json

import httpx
import pytest
import respx

from backend.app.services.errors import OllamaError
from backend.app.services.ollama import _MAX_HISTORY_CHARS, OllamaService

pytestmark = pytest.mark.anyio


def service(**overrides) -> OllamaService:
    return OllamaService(
        base_url="http://ollama.test",
        model="test-model",
        timeout_seconds=5,
        num_predict=128,
        **overrides,
    )


@respx.mock
async def test_health_check_success_and_failure():
    respx.get("http://ollama.test/api/tags").mock(
        return_value=httpx.Response(200, json={"models": []})
    )
    assert await service().health_check() is True
    respx.reset()

    respx.get("http://ollama.test/api/tags").mock(return_value=httpx.Response(500))
    assert await service().health_check() is False
    respx.reset()

    respx.get("http://ollama.test/api/tags").mock(side_effect=httpx.ConnectError("refused"))
    assert await service().health_check() is False


@respx.mock
async def test_list_models_sorts_names_and_raises_on_failure():
    route = respx.get("http://ollama.test/api/tags").mock(
        return_value=httpx.Response(
            200,
            json={
                "models": [
                    {"name": "qwen3:8b"},
                    {"name": "nomic-embed-text"},
                    {"name": ""},
                    {},
                ]
            },
        )
    )

    assert await service().list_models() == ["nomic-embed-text", "qwen3:8b"]
    assert route.called
    respx.reset()

    respx.get("http://ollama.test/api/tags").mock(return_value=httpx.Response(503))
    with pytest.raises(OllamaError, match="Unable to reach Ollama"):
        await service().list_models()


@respx.mock
async def test_chat_builds_payload_and_strips_thinking():
    route = respx.post("http://ollama.test/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={"message": {"content": "<think>internal reasoning</think>Hello there."}},
        )
    )

    result = await service().chat(
        "Current question",
        history=[
            {"role": "user", "content": "Earlier question"},
            {"role": "assistant", "content": "Earlier answer"},
            {"role": "system", "content": "ignored"},
            {"role": "user", "content": ""},
        ],
        system_prompt="You are Support AI.",
        num_predict=64,
        temperature=0.1,
    )

    assert result == "Hello there."
    payload = json.loads(route.calls[0].request.content)
    assert payload["model"] == "test-model"
    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["options"]["num_predict"] == 64
    assert payload["options"]["temperature"] == 0.1
    assert payload["messages"] == [
        {"role": "system", "content": "You are Support AI."},
        {"role": "user", "content": "Earlier question"},
        {"role": "assistant", "content": "Earlier answer"},
        {"role": "user", "content": "Current question"},
    ]


@respx.mock
async def test_chat_json_mode_sets_format():
    route = respx.post("http://ollama.test/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={"message": {"content": '{"facts": []}'}},
        )
    )

    result = await service().chat_json("Extract facts", num_predict=99)

    assert result == {"facts": []}
    payload = json.loads(route.calls[0].request.content)
    assert payload["format"] == "json"
    assert payload["options"]["num_predict"] == 99
    assert payload["options"]["temperature"] == 0.0


@respx.mock
async def test_chat_errors():
    respx.post("http://ollama.test/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={"message": {"content": "   "}},
        )
    )
    with pytest.raises(OllamaError, match="empty response"):
        await service().chat("Hello")
    respx.reset()

    respx.post("http://ollama.test/api/chat").mock(return_value=httpx.Response(500))
    with pytest.raises(OllamaError, match="unavailable"):
        await service().chat("Hello")
    respx.reset()

    respx.post("http://ollama.test/api/chat").mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(OllamaError, match="unavailable"):
        await service().chat("Hello")
    respx.reset()

    respx.post("http://ollama.test/api/chat").mock(
        return_value=httpx.Response(200, content=b"not json")
    )
    with pytest.raises(OllamaError, match="unavailable"):
        await service().chat("Hello")
    respx.reset()

    respx.post("http://ollama.test/api/chat").mock(
        return_value=httpx.Response(200, json=["unexpected"])
    )
    with pytest.raises(OllamaError, match="unexpected response"):
        await service().chat("Hello")


@respx.mock
async def test_chat_json_rejects_invalid_payloads():
    respx.post("http://ollama.test/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={"message": {"content": "not json"}},
        )
    )
    with pytest.raises(OllamaError, match="invalid JSON"):
        await service().chat_json("Extract")
    respx.reset()

    respx.post("http://ollama.test/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={"message": {"content": "[1, 2, 3]"}},
        )
    )
    with pytest.raises(OllamaError, match="unexpected JSON value"):
        await service().chat_json("Extract")


def test_trim_history_filters_roles_and_limits_count():
    history = [
        {"role": "system", "content": "ignored"},
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": ""},
        {"role": "assistant", "content": "two"},
        {"role": "user", "content": "three"},
    ]

    trimmed = OllamaService._trim_history(history)

    assert trimmed == [
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": "two"},
        {"role": "user", "content": "three"},
    ]


def test_trim_history_enforces_character_budget(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.ollama.settings.ollama_history_messages",
        10,
    )
    history = [
        {"role": "user", "content": "a" * 7_000},
        {"role": "assistant", "content": "b" * 7_000},
    ]

    trimmed = OllamaService._trim_history(history)

    assert trimmed == [{"role": "assistant", "content": "b" * 7_000}]
    assert len(trimmed[0]["content"]) < _MAX_HISTORY_CHARS

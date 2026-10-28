from __future__ import annotations

import pytest

from backend.app.services.errors import OllamaError
from backend.app.services.memory import (
    ExtractedFact,
    MemoryExtractor,
    _compact,
    _normalize_fact,
)

pytestmark = pytest.mark.anyio


class StubOllama:
    def __init__(self, data=None, error: Exception | None = None) -> None:
        self.data = data if data is not None else {"facts": []}
        self.error = error
        self.calls: list[tuple[str, int]] = []

    async def chat_json(self, prompt: str, num_predict: int = 400) -> dict:
        self.calls.append((prompt, num_predict))
        if self.error is not None:
            raise self.error
        return self.data


async def test_extract_returns_empty_for_blank_message():
    ollama = StubOllama()
    extractor = MemoryExtractor(ollama)

    assert await extractor.extract("   ") == []
    assert ollama.calls == []


async def test_extract_normalizes_deduplicates_and_limits_facts():
    ollama = StubOllama(
        {
            "facts": [
                {"kind": "issue", "text": "wifi drops"},
                {"kind": "preference", "text": "Customer prefers concise answers."},
                {"kind": "unknown", "text": "  --  Customer uses Ubuntu  "},
                {"kind": "name", "text": "customer is Sarah"},
                {"kind": "other", "text": "The customer likes tea"},
                {"kind": "other", "text": "ab"},
                {"kind": "other", "text": ""},
                "not-a-dict",
                {"kind": "issue", "text": "WIFI DROPS"},
                {"kind": "other", "text": "Customer has a backup laptop."},
                {"kind": "other", "text": "Customer has a work phone."},
                {"kind": "other", "text": "Customer has a tablet."},
                {"kind": "other", "text": "Customer has a printer."},
                {"kind": "other", "text": "Customer has a monitor."},
                {"kind": "other", "text": "Customer has a keyboard."},
                {"kind": "other", "text": "Customer has a mouse."},
            ]
        }
    )

    facts = await MemoryExtractor(ollama).extract("My Wi-Fi drops.")

    assert len(facts) == 8
    assert facts[0] == ExtractedFact(
        kind="issue",
        text="Customer reports: wifi drops.",
    )
    assert facts[1] == ExtractedFact(
        kind="preference",
        text="Customer prefers concise answers.",
    )
    assert facts[2] == ExtractedFact(
        kind="other",
        text="Customer uses Ubuntu.",
    )
    assert facts[3] == ExtractedFact(
        kind="name",
        text="Customer is Sarah.",
    )
    assert facts[4] == ExtractedFact(
        kind="other",
        text="The customer likes tea.",
    )
    assert len({fact.text for fact in facts}) == 8
    assert ollama.calls[0][1] == 450


async def test_extract_handles_invalid_payloads_and_errors():
    not_a_list = StubOllama({"facts": "nope"})
    assert await MemoryExtractor(not_a_list).extract("Hello") == []

    missing = StubOllama({})
    assert await MemoryExtractor(missing).extract("Hello") == []

    ollama_error = StubOllama(error=OllamaError("down"))
    assert await MemoryExtractor(ollama_error).extract("Hello") == []

    unexpected = StubOllama(error=RuntimeError("boom"))
    assert await MemoryExtractor(unexpected).extract("Hello") == []


def test_normalize_fact_variants():
    assert _normalize_fact("ab") == ""
    assert _normalize_fact("  hello   world  ") == "Customer reports: hello world."
    assert _normalize_fact("customer likes tea") == "Customer likes tea."
    assert _normalize_fact("The customer likes tea") == "The customer likes tea."
    assert _normalize_fact("Customer is happy!") == "Customer is happy!"

    long = "Customer " + "x" * 300
    normalized = _normalize_fact(long)
    assert len(normalized) <= 240
    assert normalized.startswith("Customer ")


def test_summarize_turn_compacts_both_sides():
    summary = MemoryExtractor.summarize_turn(
        "  Customer   says hello.  ",
        "Assistant says " + "a" * 2_000,
    )

    assert summary.startswith("Support interaction.\nCustomer: Customer says hello.")
    assert "Assistant: Assistant says aaa" in summary
    assert summary.endswith("…")
    assert "\n\n" not in summary


def test_compact_keeps_short_text_and_truncates_long_text():
    assert _compact("  short   text ", 50) == "short text"
    compacted = _compact("x" * 100, 10)
    assert compacted == "x" * 9 + "…"

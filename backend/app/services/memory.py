from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from backend.app.services.errors import OllamaError
from backend.app.services.ollama import OllamaService

logger = logging.getLogger(__name__)

_ALLOWED_KINDS = {
    "name",
    "company",
    "product",
    "operating_system",
    "issue",
    "preference",
    "account",
    "contact",
    "other",
}

_EXTRACTION_PROMPT = """You extract durable customer-support facts from one customer message.

Return JSON only, exactly in this shape:
{{"facts":[{{"kind":"name|company|product|operating_system|issue|preference|account|contact|other","text":"short third-person fact"}}]}}

Rules:
- Only include facts the customer explicitly stated. Never invent details.
- Each text must be a short sentence beginning with "Customer".
- Capture the customer's name, company, product/device, operating system,
  recurring issue, response preference, account context, and prior support details.
- Do not include greetings, questions, or advice from the assistant.
- Return at most 8 facts. If there are no durable facts, return {{"facts":[]}}.

Customer message:
\"\"\"{message}\"\"\"
"""


@dataclass(frozen=True)
class ExtractedFact:
    kind: str
    text: str


class MemoryExtractor:
    """Turns a chat message into a small set of durable customer facts.

    Hindsight is excellent at storing and retrieving memories. This extractor
    makes the *selection* step explicit and deterministic: the application
    decides which durable facts are worth keeping before they are retained.
    """

    def __init__(self, ollama: OllamaService) -> None:
        self.ollama = ollama

    async def extract(self, message: str) -> list[ExtractedFact]:
        message = message.strip()
        if not message:
            return []

        prompt = _EXTRACTION_PROMPT.format(message=message[:4_000])

        try:
            data = await self.ollama.chat_json(prompt, num_predict=450)
        except OllamaError:
            logger.warning("Memory extraction failed; retaining the raw turn.")
            return []
        except Exception:
            logger.exception("Unexpected memory extraction failure")
            return []

        raw_facts = data.get("facts", [])
        if not isinstance(raw_facts, list):
            return []

        facts: list[ExtractedFact] = []
        seen: set[str] = set()

        for item in raw_facts:
            if not isinstance(item, dict):
                continue

            text = _normalize_fact(str(item.get("text", "")))
            if not text:
                continue

            kind = str(item.get("kind", "other")).strip().lower()
            if kind not in _ALLOWED_KINDS:
                kind = "other"

            key = text.casefold()
            if key in seen:
                continue

            seen.add(key)
            facts.append(ExtractedFact(kind=kind, text=text))

            if len(facts) >= 8:
                break

        return facts

    @staticmethod
    def summarize_turn(user_text: str, assistant_text: str) -> str:
        user_text = _compact(user_text, 900)
        assistant_text = _compact(assistant_text, 1_400)
        return f"Support interaction.\nCustomer: {user_text}\nAssistant: {assistant_text}"


def _normalize_fact(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip().strip("-• ").strip("\"'")
    if len(text) < 3:
        return ""

    if not text.startswith(("Customer", "The customer")):
        if text.lower().startswith("customer"):
            text = "Customer" + text[len("customer") :]
        else:
            text = f"Customer reports: {text}"

    text = text[:239].rstrip()
    if text and text[-1] not in ".!?":
        text += "."
    return text


def _compact(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from backend.app.config import settings
from backend.app.services.errors import HindsightError
from backend.app.services.memory import ExtractedFact, MemoryExtractor

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MemoryRecord:
    id: str
    text: str
    kind: str = "other"
    source: str = "memory"
    context: str | None = None
    created_at: datetime | None = None
    score: float | None = None


class HindsightClient:
    """Hindsight adapter with one isolated memory bank per customer.

    A bank per customer makes recall scoping structural rather than a filter
    that a future query might forget. Deleting a customer can also delete the
    complete memory history in one operation.
    """

    def __init__(
        self,
        base_url: str | None = None,
        bank_prefix: str | None = None,
        timeout_seconds: float | None = None,
        enabled: bool | None = None,
    ) -> None:
        self.base_url = (base_url or settings.hindsight_base_url).rstrip("/")
        self.bank_prefix = bank_prefix or settings.hindsight_bank_prefix
        self.timeout_seconds = timeout_seconds or settings.hindsight_timeout_seconds
        self.enabled = settings.hindsight_enabled if enabled is None else enabled
        self._ensured_banks: set[str] = set()
        self._ensure_lock = asyncio.Lock()

    def bank_id(self, memory_key: str) -> str:
        return f"{self.bank_prefix}-{memory_key}"

    async def health_check(self) -> bool:
        if not self.enabled:
            return False

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                return True
        except Exception:
            return False

    async def ensure_bank(self, memory_key: str) -> str:
        bank_id = self.bank_id(memory_key)
        if bank_id in self._ensured_banks:
            return bank_id

        async with self._ensure_lock:
            if bank_id in self._ensured_banks:
                return bank_id

            config = {
                "name": bank_id,
                # The application performs fact selection itself. "chunks"
                # preserves those exact facts and makes retain fast and
                # deterministic; Hindsight still owns semantic recall.
                "retain_extraction_mode": "chunks",
                "enable_observations": False,
            }

            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.patch(
                        f"{self.base_url}/v1/default/banks/{bank_id}",
                        json=config,
                    )
                    if response.status_code == 404:
                        response = await client.put(
                            f"{self.base_url}/v1/default/banks/{bank_id}",
                            json=config,
                        )
                    response.raise_for_status()
            except httpx.HTTPError as exc:
                raise HindsightError(
                    "The memory service could not create a customer bank."
                ) from exc

            self._ensured_banks.add(bank_id)
            return bank_id

    async def prepare_retain(self, memory_key: str, limit: int = 200) -> set[str]:
        """Warm the bank and load existing fact text before the model reply.

        This runs while Ollama is generating, so the only Hindsight work left
        on the response path is the retain request itself.
        """
        if not self.enabled:
            return set()

        await self.ensure_bank(memory_key)
        try:
            existing = await self.list_memories(memory_key, limit=limit)
        except HindsightError:
            logger.warning("Could not check for duplicate memories")
            return set()
        return {record.text.casefold() for record in existing}

    async def retain_turn(
        self,
        memory_key: str,
        conversation_id: int,
        user_text: str,
        assistant_text: str,
        facts: list[ExtractedFact] | None = None,
        existing_texts: set[str] | None = None,
    ) -> bool:
        if not self.enabled:
            return False

        bank_id = await self.ensure_bank(memory_key)
        document_id = f"conversation-{conversation_id}"

        if existing_texts is None:
            existing_texts = set()
            try:
                existing = await self.list_memories(memory_key, limit=200)
                existing_texts = {record.text.casefold() for record in existing}
            except HindsightError:
                logger.warning("Could not check for duplicate memories")

        items: list[dict[str, object]] = []

        for fact in facts or []:
            if fact.text.casefold() in existing_texts:
                continue

            items.append(
                {
                    "content": fact.text,
                    "document_id": document_id,
                    "context": "customer profile fact",
                    "metadata": {
                        "kind": fact.kind,
                        "source": "profile_extraction",
                    },
                    "tags": ["customer-support"],
                }
            )

        # Retaining the turn as well preserves the human context and the
        # support advice, not just the extracted profile fields.
        items.append(
            {
                "content": MemoryExtractor.summarize_turn(user_text, assistant_text),
                "document_id": document_id,
                "context": "support interaction",
                "metadata": {
                    "kind": "interaction",
                    "source": "conversation",
                },
                "tags": ["customer-support"],
            }
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/v1/default/banks/{bank_id}/memories",
                    json={"items": items, "async": False},
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HindsightError("The memory service could not retain this conversation.") from exc

        return True

    async def recall(
        self,
        memory_key: str,
        query: str,
        limit: int | None = None,
    ) -> list[MemoryRecord]:
        if not self.enabled:
            return []

        bank_id = self.bank_id(memory_key)

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/v1/default/banks/{bank_id}/memories/recall",
                    json={
                        "query": query,
                        "max_tokens": 1_200,
                        "prefer_observations": True,
                    },
                )
                if response.status_code == 404:
                    return []
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HindsightError("The memory service could not recall customer context.") from exc

        records: list[MemoryRecord] = []
        seen: set[str] = set()

        for result in data.get("results", []):
            if not isinstance(result, dict):
                continue

            text = str(result.get("text", "")).strip()
            if not text:
                continue

            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)

            metadata = result.get("metadata") or {}
            if not isinstance(metadata, dict):
                metadata = {}

            records.append(
                MemoryRecord(
                    id=str(result.get("id", "")),
                    text=text,
                    kind=str(metadata.get("kind", "other")),
                    source=str(metadata.get("source", "memory")),
                    context=result.get("context"),
                    created_at=_parse_datetime(
                        result.get("mentioned_at") or result.get("occurred_start")
                    ),
                    score=_score(result.get("scores")),
                )
            )

        limit = limit or settings.hindsight_recall_limit
        return records[:limit]

    async def list_memories(
        self,
        memory_key: str,
        limit: int = 100,
    ) -> list[MemoryRecord]:
        if not self.enabled:
            return []

        bank_id = self.bank_id(memory_key)

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(
                    f"{self.base_url}/v1/default/banks/{bank_id}/memories/list",
                    params={"limit": limit, "offset": 0},
                )
                if response.status_code == 404:
                    return []
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HindsightError("The memory service could not list customer memories.") from exc

        records: list[MemoryRecord] = []
        seen: set[str] = set()

        for item in data.get("items", []):
            if not isinstance(item, dict):
                continue

            text = str(item.get("text", "")).strip()
            if not text:
                continue

            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)

            metadata = item.get("metadata") or {}
            if not isinstance(metadata, dict):
                metadata = {}

            records.append(
                MemoryRecord(
                    id=str(item.get("id", "")),
                    text=text,
                    kind=str(metadata.get("kind", "other")),
                    source=str(metadata.get("source", "memory")),
                    context=item.get("context"),
                    created_at=_parse_datetime(item.get("date") or item.get("mentioned_at")),
                )
            )

        return records

    async def delete_bank(self, memory_key: str) -> bool:
        if not self.enabled:
            return False

        bank_id = self.bank_id(memory_key)

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.delete(f"{self.base_url}/v1/default/banks/{bank_id}")
                if response.status_code == 404:
                    self._ensured_banks.discard(bank_id)
                    return True
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HindsightError(
                "The memory service could not delete this customer's bank."
            ) from exc

        self._ensured_banks.discard(bank_id)
        return True


def _parse_datetime(value: object) -> datetime | None:
    if not value or not isinstance(value, str):
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _score(value: object) -> float | None:
    if not isinstance(value, dict):
        return None

    score = value.get("final")
    if isinstance(score, (int, float)):
        return float(score)
    return None

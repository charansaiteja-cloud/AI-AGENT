from __future__ import annotations

import httpx

from backend.app.config import settings


class HindsightClient:
    def __init__(
        self,
        base_url: str | None = None,
        bank_id: str | None = None,
    ):
        self.base_url = (
            base_url or settings.hindsight_base_url
        ).rstrip("/")

        self.bank_id = (
            bank_id or settings.hindsight_bank_id
        )

    async def health(self) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.base_url}/health"
            )
            response.raise_for_status()
            return response.json()

    async def retain(
        self,
        content: str,
        conversation_id: str,
        tags: list[str] | None = None,
        context: str | None = None,
    ) -> dict:
        item = {
            "content": content,
            "document_id": conversation_id,
        }

        if tags:
            item["tags"] = tags

        if context:
            item["context"] = context

        payload = {
            "items": [item],
            "async": True,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/default/banks/"
                f"{self.bank_id}/memories",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def recall(
        self,
        query: str,
        max_tokens: int = 1500,
    ) -> dict:
        payload = {
            "query": query,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/default/banks/"
                f"{self.bank_id}/memories/recall",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def recall_text(
        self,
        query: str,
        max_tokens: int = 1500,
    ) -> str:
        data = await self.recall(
            query=query,
            max_tokens=max_tokens,
        )

        results = data.get("results", [])

        if not results:
            return ""

        lines: list[str] = []
        seen: set[str] = set()

        for result in results:
            text = result.get("text")

            if not text:
                continue

            # Normalize Hindsight's derived "world" facts.
            base_text = text.split(" | When:")[0].strip()

            # Only expose customer-related facts to the LLM.
            # Assistant observations and generated conversation summaries
            # can otherwise pollute the customer profile.
            lowered = base_text.lower()

            if lowered.startswith("assistant "):
                continue

            if base_text in seen:
                continue

            seen.add(base_text)
            lines.append(f"- {base_text}")

        return "\n".join(lines)

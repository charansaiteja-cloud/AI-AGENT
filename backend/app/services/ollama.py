from __future__ import annotations

import logging
import re

import httpx

from backend.app.config import settings
from backend.app.services.errors import OllamaError

logger = logging.getLogger(__name__)

_THINKING_PATTERN = re.compile(r"<think\b[^>]*>.*?</think>", re.DOTALL | re.IGNORECASE)
_MAX_HISTORY_CHARS = 12_000


class OllamaService:
    """Small, testable adapter around Ollama's HTTP chat API."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        num_predict: int | None = None,
    ) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout_seconds = timeout_seconds or settings.ollama_timeout_seconds
        self.num_predict = num_predict or settings.ollama_num_predict

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                return True
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise OllamaError("Unable to reach Ollama.") from exc

        if not isinstance(data, dict):
            raise OllamaError("Ollama returned an unexpected response.")

        return sorted(
            model["name"]
            for model in data.get("models", [])
            if isinstance(model, dict) and model.get("name")
        )

    async def chat(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        system_prompt: str | None = None,
        *,
        json_mode: bool = False,
        num_predict: int | None = None,
        temperature: float | None = None,
    ) -> str:
        messages = self._build_messages(message, history, system_prompt)

        payload: dict[str, object] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            # Qwen3 and other thinking models otherwise spend the entire
            # response budget inside the hidden reasoning channel.
            "think": False,
            "options": {
                "num_predict": num_predict or self.num_predict,
                "temperature": (
                    settings.ollama_temperature if temperature is None else temperature
                ),
                "top_k": 20,
                "top_p": 0.8,
            },
        }

        if json_mode:
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Ollama chat request failed: %s", type(exc).__name__)
            raise OllamaError("The language model is unavailable.") from exc

        if not isinstance(data, dict):
            raise OllamaError("The language model returned an unexpected response.")

        message = data.get("message", {})
        content = message.get("content", "") if isinstance(message, dict) else ""
        content = _THINKING_PATTERN.sub("", content).strip()

        if not content:
            raise OllamaError("The language model returned an empty response.")

        return content

    async def chat_json(
        self,
        prompt: str,
        *,
        num_predict: int = 400,
    ) -> dict:
        content = await self.chat(
            prompt,
            json_mode=True,
            num_predict=num_predict,
            temperature=0.0,
        )

        try:
            import json

            parsed = json.loads(content)
        except ValueError as exc:
            raise OllamaError("The model returned invalid JSON.") from exc

        if not isinstance(parsed, dict):
            raise OllamaError("The model returned an unexpected JSON value.")

        return parsed

    def _build_messages(
        self,
        message: str,
        history: list[dict[str, str]] | None,
        system_prompt: str | None,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.extend(self._trim_history(history or []))
        messages.append({"role": "user", "content": message})
        return messages

    @staticmethod
    def _trim_history(
        history: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        usable = [
            {"role": item["role"], "content": item["content"]}
            for item in history
            if item.get("role") in {"user", "assistant"} and item.get("content")
        ]

        usable = usable[-settings.ollama_history_messages :]

        trimmed: list[dict[str, str]] = []
        characters = 0

        for item in reversed(usable):
            characters += len(item["content"])
            if characters > _MAX_HISTORY_CHARS and trimmed:
                break
            trimmed.append(item)

        trimmed.reverse()
        return trimmed

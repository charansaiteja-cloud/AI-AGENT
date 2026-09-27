import httpx

from backend.app.config import settings


class OllamaService:
    def __init__(self):
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                return True
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()

            return [
                model["name"]
                for model in data.get("models", [])
            ]

    async def chat(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        system_prompt: str | None = None,
    ) -> str:
        history = history or []

        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt,
            })

        # Only include recent history that is useful for continuity.
        # The current user message must remain the final user turn.
        # When a system prompt contains customer-specific facts,
        # keep the request isolated from stale conversation context.
        if not system_prompt:
            messages.extend(history[-4:])

        messages.append({
            "role": "user",
            "content": message,
        })

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": 150,
                "temperature": 0.2,
                "top_k": 20,
                "top_p": 0.8,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()

            data = response.json()

            return data["message"]["content"]

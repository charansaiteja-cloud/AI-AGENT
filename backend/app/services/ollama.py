import httpx

from backend.app.config import settings


class OllamaService:
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/tags"
                )
                response.raise_for_status()
                return True
        except (httpx.HTTPError, httpx.RequestError):
            return False

    async def list_models(self) -> list[str]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.base_url}/api/tags"
            )
            response.raise_for_status()

            data = response.json()

            return [
                model["name"]
                for model in data.get("models", [])
            ]

    async def chat(self, message: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": message,
                }
            ],
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()

            data = response.json()

            return data["message"]["content"]

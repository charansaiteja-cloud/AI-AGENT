import httpx

from backend.app.config import settings


SYSTEM_PROMPT = """You are a professional customer support assistant.

Your responsibilities:
- Help customers clearly and politely.
- Explain technical and business topics in simple language.
- For banking, payments, sales, accounts, or financial topics, provide general information only.
- Never invent account details, transactions, policies, prices, or company rules.
- If you do not have enough information, say so and ask a useful follow-up question.
- Keep responses concise but helpful.
- Use bullet points when they improve readability.
"""


class OllamaService:
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/tags"
                )
                response.raise_for_status()
                return True
        except httpx.HTTPError:
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
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": message,
                },
            ],
            "stream": False,
        }

        timeout = httpx.Timeout(
            connect=5.0,
            read=60.0,
            write=10.0,
            pool=5.0,
        )

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )

                response.raise_for_status()

                data = response.json()

                content = data.get("message", {}).get("content")

                if not content:
                    raise RuntimeError(
                        "Ollama returned an empty response"
                    )

                return content.strip()

        except httpx.TimeoutException as exc:
            raise RuntimeError(
                "Ollama response timed out"
            ) from exc

        except httpx.ConnectError as exc:
            raise RuntimeError(
                "Unable to connect to Ollama"
            ) from exc

        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Ollama returned HTTP {exc.response.status_code}"
            ) from exc

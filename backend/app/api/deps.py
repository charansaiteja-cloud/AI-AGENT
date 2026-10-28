from fastapi import Depends

from backend.app.services.attachments import AttachmentService
from backend.app.services.hindsight import HindsightClient
from backend.app.services.memory import MemoryExtractor
from backend.app.services.ollama import OllamaService
from backend.app.services.rate_limit import SlidingWindowLimiter

ollama_service = OllamaService()
hindsight_service = HindsightClient()
attachment_service = AttachmentService()
rate_limiter = SlidingWindowLimiter()


def get_ollama() -> OllamaService:
    return ollama_service


def get_hindsight() -> HindsightClient:
    return hindsight_service


def get_attachment_service() -> AttachmentService:
    return attachment_service


def get_rate_limiter() -> SlidingWindowLimiter:
    return rate_limiter


def get_memory_extractor(
    ollama: OllamaService = Depends(get_ollama),
) -> MemoryExtractor:
    return MemoryExtractor(ollama)

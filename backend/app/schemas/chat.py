from pydantic import BaseModel, Field

from backend.app.schemas.memory import MemoryOut


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4_000)
    conversation_id: int | None = None
    customer_id: int | None = None
    attachment_ids: list[int] = Field(default_factory=list, max_length=5)


class ChatResponse(BaseModel):
    response: str
    model: str
    conversation_id: int
    customer_id: int
    conversation_title: str
    user_message_id: int
    assistant_message_id: int
    memories: list[MemoryOut] = []
    memory_used: bool = False
    memory_saved: bool = False
    latency_ms: int = 0

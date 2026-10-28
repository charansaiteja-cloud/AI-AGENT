from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    database: str
    ollama: str
    hindsight: str
    model: str


class ModelListResponse(BaseModel):
    models: list[str]
    active_model: str

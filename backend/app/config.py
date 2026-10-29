from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env."""

    app_name: str = "Support AI"
    app_description: str = "A customer support agent with durable, per-customer long-term memory."
    app_version: str = "1.0.0"
    environment: Literal["development", "production", "test"] = "development"
    debug: bool = False
    api_prefix: str = "/api"
    app_api_key: str | None = None

    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'support_agent.db'}"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    ollama_timeout_seconds: float = 180.0
    ollama_num_predict: int = 512
    ollama_history_messages: int = 20
    ollama_temperature: float = 0.2

    hindsight_base_url: str = "http://127.0.0.1:8888"
    hindsight_bank_prefix: str = "support-customer"
    hindsight_timeout_seconds: float = 30.0
    hindsight_enabled: bool = True
    hindsight_recall_limit: int = 8

    upload_dir: Path = BASE_DIR / "data" / "uploads"
    max_upload_size: int = 10 * 1024 * 1024
    allowed_upload_extensions: str = ".png,.jpg,.jpeg,.gif,.webp,.txt,.md,.csv,.json,.pdf"
    max_attachment_text_chars: int = 20_000
    max_message_length: int = 4_000
    max_attachments_per_message: int = 5

    static_dir: Path = BASE_DIR / "frontend" / "dist"

    rate_limit_enabled: bool = True
    rate_limit_chat_per_minute: int = 60
    rate_limit_upload_per_minute: int = 30

    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("app_api_key")
    @classmethod
    def _blank_key_is_disabled(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("upload_dir", "static_dir", mode="before")
    @classmethod
    def _expand_path(cls, value: object) -> Path:
        return Path(str(value)).expanduser()

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_extensions(self) -> set[str]:
        return {
            extension.strip().lower()
            for extension in self.allowed_upload_extensions.split(",")
            if extension.strip()
        }

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def api_auth_enabled(self) -> bool:
        return bool(self.app_api_key)


settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    max_upload_size: int = 10 * 1024 * 1024
    app_name: str = "Customer Support Agent"
    app_version: str = "0.2.0"
    debug: bool = True

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"

    hindsight_base_url: str = "http://127.0.0.1:8888"
    hindsight_bank_id: str = "customer-support"

    database_url: str = "sqlite+aiosqlite:///./data/support_agent.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Customer Support Agent"
    app_version: str = "0.1.0"
    debug: bool = True

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

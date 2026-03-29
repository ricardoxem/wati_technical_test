from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"

    llm_provider: str = "ollama"
    ollama_model: str = "llama3.1:8b"
    ollama_host: str = "http://localhost:11434"
    ollama_timeout_seconds: float = 300.0

    openai_model: str = "gpt-4o-mini"
    openai_api_key: str | None = None

    wati_backend: str = "mock"
    wati_base_url: str = "http://127.0.0.1:8001"
    wati_api_token: str = "mock-token"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()

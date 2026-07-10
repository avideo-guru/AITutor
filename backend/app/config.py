from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """App configuration, overridable via environment variables or backend/.env."""

    # "mock" (no key needed) | "anthropic" — later: "ollama", "own-model"
    llm_provider: str = "mock"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5"

    database_url: str = "sqlite:///./aitutor.db"
    cors_origins: list[str] = ["http://localhost:4200"]

    class Config:
        env_file = ".env"


settings = Settings()

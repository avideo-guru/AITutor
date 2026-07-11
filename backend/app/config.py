from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # Empty defaults keep imports side-effect free (tests, tooling); anything
    # unset fails loudly at first use, not at import.
    database_url: str = ""

    supabase_url: str = ""
    supabase_service_role_key: str = ""

    deepseek_api_key: str = ""
    gemini_api_key: str = ""

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""

    frontend_url: str = "http://localhost:8081"
    free_daily_limit: int = 10
    sentry_dsn: str = ""


settings = Settings()

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
    # Which Gemini model the adapter calls (vision + failover). Zero-spend
    # phase runs "gemini-2.5-flash" — 2.5-pro is NOT on the Gemini free tier
    # (see docs/Status.md § zero-spend guardrails). Default = paid-tier model
    # so behavior is unchanged unless explicitly configured.
    gemini_model: str = "gemini-2.5-pro"

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""

    frontend_url: str = "http://localhost:8081"
    free_daily_limit: int = 10
    pro_monthly_limit: int = 1500
    sentry_dsn: str = ""


settings = Settings()

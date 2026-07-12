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

    # SSRF guard for /v1/ask image_url (the backend fetches it server-side).
    # Empty prefix -> derived from supabase_url (the app's upload bucket);
    # if neither is set, image questions are rejected (fail closed).
    image_url_allowed_prefix: str = ""
    max_image_bytes: int = 4 * 1024 * 1024


settings = Settings()


def allowed_image_prefix() -> str | None:
    """The only URL prefix the backend will fetch images from. None = no
    prefix configured -> reject all image questions (fail closed, SSRF)."""
    if settings.image_url_allowed_prefix:
        return settings.image_url_allowed_prefix
    if settings.supabase_url:
        return f"{settings.supabase_url}/storage/v1/object/public/"
    return None


from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql://research:research@localhost:5432/research_marketplace"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret: str = "changeme-use-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
    refresh_token_expire_days: int = 7

    # WhatsApp
    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""
    whatsapp_verify_token: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""

    # PayPal
    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_mode: str = "sandbox"  # sandbox | live

    # AWS S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_bucket_name: str = "research-marketplace"
    aws_region: str = "us-east-1"

    # Upload limits
    max_upload_mb: int = 50

    # Rate limiting
    rate_limit_per_minute: int = 100

    # Application
    environment: str = "development"

    # CORS — comma-separated list of allowed origins stored as a string so it
    # can be read from a single env var; the property below converts it.
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def access_token_expire_minutes(self) -> int:
        return self.jwt_expire_hours * 60


@lru_cache
def get_settings() -> Settings:
    return Settings()

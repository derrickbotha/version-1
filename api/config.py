from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # App
    APP_NAME: str = "ASA v2 - Agentic Scholar Assistant"
    DEBUG: bool = False
    SECRET_KEY: str = "changeme-use-a-long-random-secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://asa:asa@localhost:5432/asa_platform"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI APIs
    PERPLEXITY_API_KEY: str = ""
    PERPLEXITY_API_URL: str = "https://api.perplexity.ai/chat/completions"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_URL: str = "https://api.deepseek.com/chat/completions"

    # Plagiarism
    COPYLEAKS_API_KEY: str = ""
    COPYLEAKS_EMAIL: str = ""

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # PayPal
    PAYPAL_CLIENT_ID: str = ""
    PAYPAL_CLIENT_SECRET: str = ""
    PAYPAL_BASE_URL: str = "https://api-m.sandbox.paypal.com"

    # Email (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "asa@scholarassistant.ai"

    # S3 / file storage
    S3_ENDPOINT: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "asa-documents"

    # n8n
    N8N_BASE_URL: str = "http://localhost:5678"
    N8N_API_KEY: str = ""

    # Professor review pricing
    PROFESSOR_REVIEW_COST_USD: float = 20.0

    # Plans (USD/month)
    PLAN_PRICES: dict = {
        "starter":      199.0,
        "professional": 299.0,
        "agentic_pro":  399.0,
        "enterprise":   0.0,   # custom billing
    }

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()

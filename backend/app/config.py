from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "synaptiverse"
    app_environment: str = "development"
    log_level: str = "INFO"
    audit_retention_days: int = 365
    session_retention_days: int = 30
    lead_retention_days: int = 180
    database_url: str = f"sqlite+aiosqlite:///{Path(__file__).resolve().parent.parent / 'synaptiverse.db'}"
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False
    redis_key_prefix: str = "synaptiverse"
    auth_rate_limit: int = 10
    public_intake_rate_limit: int = 30
    channel_webhook_secret: str = "change-me"
    whatsapp_verify_token: str = "change-me"
    neo4j_uri: str = "neo4j://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j"
    neo4j_database: str = "neo4j"
    neo4j_enabled: bool = False
    auth_access_minutes: int = 15
    auth_refresh_days: int = 14
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"
    default_tenant_id: str = "11111111-1111-1111-1111-111111111111"
    auto_create_schema: bool = True
    cors_origins: str = "http://127.0.0.1:3000,http://localhost:3000"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        normalized = str(value)
        if normalized.startswith("postgres://"):
            normalized = normalized.replace("postgres://", "postgresql+asyncpg://", 1)
        elif normalized.startswith("postgresql://"):
            normalized = normalized.replace("postgresql://", "postgresql+asyncpg://", 1)
        return normalized.replace("sslmode=require", "ssl=require")

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        if self.app_environment == "production":
            problems = []
            if not self.database_url.startswith("postgresql+asyncpg://"):
                problems.append("DATABASE_URL must use PostgreSQL")
            if self.auto_create_schema:
                problems.append("AUTO_CREATE_SCHEMA must be false")
            if not self.auth_cookie_secure:
                problems.append("AUTH_COOKIE_SECURE must be true")
            if self.channel_webhook_secret == "change-me":
                problems.append("CHANNEL_WEBHOOK_SECRET must be replaced")
            if problems:
                raise ValueError("Unsafe production configuration: " + "; ".join(problems))
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()

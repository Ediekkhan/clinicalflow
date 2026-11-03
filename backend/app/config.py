from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", hide_input_in_errors=True)

    app_name: str = "clinicalflow"
    app_env: str = ""
    app_environment: str = "development"
    debug: str = "false"
    enable_test_fixtures: bool = False
    enable_demo_content: bool = False
    enable_lab_module: bool = False
    enable_pharmacy_module: bool = False
    enable_payer_module: bool = False
    enable_government_module: bool = False
    enable_imaging_module: bool = False
    enable_billing_module: bool = False
    enable_hackathon_providers: bool = False
    skip_phone_verification: bool = False
    default_credentials_present: bool = False
    log_level: str = "INFO"
    audit_retention_days: int = 365
    session_retention_days: int = 30
    lead_retention_days: int = 180
    database_url: str = f"sqlite+aiosqlite:///{Path(__file__).resolve().parent.parent / 'clinicalflow.db'}"
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False
    redis_key_prefix: str = "clinicalflow"
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
    auth_max_failed_attempts: int = 5
    auth_lockout_minutes: int = 15
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"
    session_secret: str = "development-only-change-me"
    default_tenant_id: str = "11111111-1111-1111-1111-111111111111"
    platform_tenant_id: str | None = None
    auto_create_schema: bool = True
    cors_origins: str = "http://127.0.0.1:3000,http://localhost:3000"
    # Optional Supabase Auth compatibility layer. Profile and tenant records
    # remain in the application schema; these values only enable identity sync.
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    supabase_jwt_secret: str | None = None
    stripe_secret_key: str | None = None
    stripe_publishable_key: str | None = None
    stripe_webhook_secret: str | None = None
    paystack_secret_key: str | None = None
    paystack_public_key: str | None = None
    paystack_webhook_secret: str | None = None
    email_provider: str | None = None
    email_api_key: str | None = None
    email_from_address: str | None = None
    email_from_name: str = "ClinicalFlow"
    email_reply_to: str | None = None
    email_webhook_secret: str | None = None
    payment_success_url: str = ""
    payment_cancel_url: str = ""
    worker_concurrency: int = 1
    worker_poll_interval_seconds: float = 2.0
    worker_max_attempts: int = 8
    worker_dead_letter_alert_threshold: int = 1
    storage_provider: str | None = None
    storage_bucket: str | None = None
    storage_region: str | None = None
    storage_endpoint: str | None = None
    storage_access_key: str | None = None
    storage_secret_key: str | None = None
    signed_url_ttl_seconds: int = 300

    @property
    def supabase_auth_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key)

    @property
    def environment(self) -> str:
        return (self.app_env or self.app_environment).strip().lower()

    @property
    def fixtures_enabled(self) -> bool:
        return self.environment == "test" and self.enable_test_fixtures

    @property
    def operational_tenant_id(self) -> str:
        """Tenant used for public platform activity outside facility workspaces."""
        return self.platform_tenant_id or self.default_tenant_id

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
        if self.environment not in {"test", "development", "staging", "production", "hackathon"}:
            raise ValueError("APP_ENV must be test, development, staging, production, or hackathon")
        production_selected = "production" in {
            self.app_env.strip().lower(),
            self.app_environment.strip().lower(),
        }
        if production_selected:
            problems = []
            if self.enable_test_fixtures or self.enable_demo_content:
                problems.append("test fixtures and demo content must be disabled")
            if self.default_credentials_present:
                problems.append("default credentials must not be enabled")
            if self.skip_phone_verification:
                problems.append("phone verification must not be skipped")
            if self.debug.strip().lower() in {"1", "true", "yes", "on"}:
                problems.append("DEBUG must be false")
            if not self.database_url.startswith("postgresql+asyncpg://"):
                problems.append("DATABASE_URL must use PostgreSQL")
            if self.auto_create_schema:
                problems.append("AUTO_CREATE_SCHEMA must be false")
            if not self.auth_cookie_secure:
                problems.append("AUTH_COOKIE_SECURE must be true")
            placeholders = {"", "change-me", "development-only-change-me"}
            if self.channel_webhook_secret.strip() in placeholders or len(self.channel_webhook_secret.strip()) < 32:
                problems.append("CHANNEL_WEBHOOK_SECRET must contain at least 32 characters")
            if self.session_secret.strip() in placeholders or len(self.session_secret.strip()) < 32:
                problems.append("SESSION_SECRET must contain at least 32 characters")
            try:
                tenant_id = UUID(self.platform_tenant_id or "")
                if tenant_id == UUID("11111111-1111-1111-1111-111111111111"):
                    raise ValueError
            except ValueError:
                problems.append("PLATFORM_TENANT_ID must be a non-demo UUID")
            origins = self.allowed_origins
            if not origins:
                problems.append("CORS_ORIGINS must contain at least one approved HTTPS origin")
            for origin in origins:
                parsed = urlsplit(origin)
                if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment or origin == "*":
                    problems.append("CORS_ORIGINS must contain only exact HTTPS origins")
                    break
            if problems:
                raise ValueError("Unsafe production configuration: " + "; ".join(problems))
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()

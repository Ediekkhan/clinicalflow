from functools import lru_cache
from uuid import UUID

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Values are deliberately simple for clinics where deployments may begin on a
    single local machine before being promoted to a managed cloud environment.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = Field(default="Synaptiverse Triage", alias="PROJECT_NAME")
    api_prefix: str = "/api/v1"
    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    neo4j_uri: str = Field(default="neo4j://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="synaptiverse_local", alias="NEO4J_PASSWORD")
    jwt_secret: str = Field(default="replace-me-before-production", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=480, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    hospital_account_password: str = Field(default="klau2mari2", alias="HOSPITAL_ACCOUNT_PASSWORD")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    demo_tenant_id: UUID = Field(
        default=UUID("00000000-0000-4000-8000-000000000001"),
        alias="DEMO_TENANT_ID",
    )
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

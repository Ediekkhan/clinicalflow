from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def set_tenant_context(session: AsyncSession, tenant_id: UUID | str) -> None:
    """Bind PostgreSQL RLS to the tenant for the current transaction only."""

    await session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": str(tenant_id)},
    )


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that guarantees every business query has tenant RLS set."""

    async with SessionLocal() as session:
        tenant_id = getattr(request.state, "tenant_id", None)
        user_type = getattr(request.state, "user_type", None)
        header_tenant_id = request.headers.get("X-Tenant-Id")

        if tenant_id:
            await set_tenant_context(session, tenant_id)
        elif request.url.path.startswith(f"{settings.api_prefix}/webhooks"):
            webhook_tenant_id = header_tenant_id or str(settings.demo_tenant_id)
            await set_tenant_context(session, webhook_tenant_id)
            request.state.tenant_id = webhook_tenant_id
        elif user_type == "PATIENT":
            await session.execute(text("SET LOCAL app.current_user_type = 'PATIENT'"))

        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


get_db = get_session

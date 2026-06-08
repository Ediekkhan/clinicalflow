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


async def set_tenant_context(session: AsyncSession, tenant_id: UUID) -> None:
    """Bind PostgreSQL RLS to the tenant for the current transaction only."""

    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that guarantees every business query has tenant RLS set."""

    tenant_id: UUID = request.state.tenant_id
    async with SessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, tenant_id)
            yield session


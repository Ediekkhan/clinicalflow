import asyncio
import unittest

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.models import Base, AuditLog
from app.services.audit_service import AuditAction, write_audit_log


class AuditServiceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, future=True)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_write_audit_log_persists_entry(self) -> None:
        async with self.session_factory() as session:
            await write_audit_log(
                session,
                AuditAction.TICKET_CREATED,
                actor_id=None,
                actor_type="SYSTEM",
                tenant_id="11111111-1111-1111-1111-111111111111",
                ip_address="127.0.0.1",
                resource_type="Ticket",
                resource_id="123",
                metadata={"channel": "WEB"},
            )
            await session.commit()

            result = await session.execute(__import__("sqlalchemy").select(AuditLog))
            rows = result.scalars().all()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].action, AuditAction.TICKET_CREATED.value)


if __name__ == "__main__":
    unittest.main()

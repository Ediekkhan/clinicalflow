"""Dedicated production outbox worker entry point for Render."""
import asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.config import settings
from app.services.outbox_worker import OutboxWorker

async def main() -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    worker = OutboxWorker(async_sessionmaker(engine, expire_on_commit=False), poll_seconds=settings.worker_poll_interval_seconds, max_attempts=settings.worker_max_attempts)
    try:
        await worker.start()
        while worker.running:
            await asyncio.sleep(1)
    finally:
        await worker.stop()
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())

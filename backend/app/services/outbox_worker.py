from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import OutboxEvent
from app.services.provider_adapters import ProviderNotConfigured, provider_registry


class OutboxWorker:
    """Durable outbox poller with bounded retries and dead-lettering."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession], *, poll_seconds: float = 2.0, max_attempts: int = 8) -> None:
        self.session_factory = session_factory
        self.poll_seconds = poll_seconds
        self.max_attempts = max_attempts
        self.running = False
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self.running = True
        self._task = asyncio.create_task(self.run())

    async def stop(self) -> None:
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def run(self) -> None:
        while self.running:
            processed = await self.process_batch()
            if processed == 0:
                await asyncio.sleep(self.poll_seconds)

    async def process_batch(self, limit: int = 50) -> int:
        async with self.session_factory() as session:
            now = datetime.now(UTC)
            events = list((await session.execute(
                select(OutboxEvent)
                .where(OutboxEvent.status == "PENDING", OutboxEvent.available_at <= now)
                .order_by(OutboxEvent.created_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )).scalars().all())
            for event in events:
                await self._process_event(session, event)
            if events:
                await session.commit()
            return len(events)

    async def _process_event(self, session: AsyncSession, event: OutboxEvent) -> None:
        event.attempts += 1
        try:
            payload = json.loads(event.payload_json or "{}")
            if not isinstance(payload, dict):
                raise ValueError("Outbox payload must be an object")
            channel = payload.get("channel")
            recipient = payload.get("recipient")
            message = payload.get("message")
            if not isinstance(channel, str) or not channel.strip():
                raise ValueError("Outbox event requires a delivery channel or a dedicated event handler")
            if not isinstance(recipient, str) or not recipient.strip():
                raise ValueError("Outbox delivery requires an explicit recipient")
            if isinstance(message, str) and message.strip():
                message = {"body": message}
            if not isinstance(message, dict) or not message:
                raise ValueError("Outbox message must be a nonempty string or object")
            provider = provider_registry().get(channel.strip().upper())
            if provider is None:
                raise ProviderNotConfigured("Unsupported delivery channel")
            await provider.deliver(
                recipient=recipient.strip(),
                payload=message,
                idempotency_key=str(event.id),
            )
            event.status = "PROCESSED"
            event.processed_at = datetime.now(UTC)
            event.last_error = None
        except Exception as error:  # pragma: no cover - provider adapters override this hook
            event.last_error = str(error)[:1000]
            if event.attempts >= self.max_attempts:
                event.status = "DEAD_LETTER"
            else:
                event.available_at = datetime.now(UTC) + timedelta(seconds=min(300, 2 ** event.attempts))


def worker_status(worker: OutboxWorker | None) -> dict[str, Any]:
    if worker is None:
        return {"status": "not_started", "running": False}
    return {"status": "running" if worker.running else "stopped", "running": worker.running}

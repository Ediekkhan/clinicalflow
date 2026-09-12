import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.outbox_worker import OutboxWorker


def make_event(payload):
    return SimpleNamespace(id=uuid4(), payload_json=json.dumps(payload), attempts=0,
                           status="PENDING", processed_at=None, last_error=None)


@pytest.mark.parametrize("message", ["Verification code", {"body": "Verification code"}])
def test_string_and_object_messages_reach_provider(monkeypatch, message):
    provider = SimpleNamespace(deliver=AsyncMock(return_value="provider-id"))
    monkeypatch.setattr("app.services.outbox_worker.provider_registry", lambda: {"EMAIL": provider})
    event = make_event({"channel": "EMAIL", "recipient": "user@example.org", "message": message})
    asyncio.run(OutboxWorker(None)._process_event(None, event))
    provider.deliver.assert_awaited_once_with(recipient="user@example.org", payload={"body": "Verification code"}, idempotency_key=str(event.id))
    assert event.status == "PROCESSED"


@pytest.mark.parametrize("payload", [[], {}, {"channel": "EMAIL", "message": "Hello"},
    {"channel": "EMAIL", "recipient": "user@example.org", "message": 123}])
def test_invalid_events_retry_and_dead_letter_without_delivery(monkeypatch, payload):
    provider = SimpleNamespace(deliver=AsyncMock())
    monkeypatch.setattr("app.services.outbox_worker.provider_registry", lambda: {"EMAIL": provider})
    event = make_event(payload)
    worker = OutboxWorker(None, max_attempts=2)
    asyncio.run(worker._process_event(None, event))
    assert event.status == "PENDING"
    assert event.processed_at is None
    asyncio.run(worker._process_event(None, event))
    assert event.status == "DEAD_LETTER"
    provider.deliver.assert_not_awaited()

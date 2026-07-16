from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any


EventHandler = Callable[[str, dict[str, Any]], Awaitable[None]]


class RedisInfrastructure:
    """Optional shared cache, limiter, and pub/sub with process-local degradation."""

    def __init__(self, *, enabled: bool, url: str, key_prefix: str = "synaptiverse") -> None:
        self.enabled = enabled
        self.url = url
        self.key_prefix = key_prefix
        self.instance_id = uuid.uuid4().hex
        self.client: Any | None = None
        self.available = False
        self._listener_task: asyncio.Task[None] | None = None
        self._local_cache: dict[str, tuple[float | None, Any]] = {}
        self._local_limits: dict[str, tuple[int, float]] = {}

    def _key(self, category: str, key: str) -> str:
        return f"{self.key_prefix}:{category}:{key}"

    async def start(self, event_handler: EventHandler | None = None) -> None:
        if not self.enabled:
            return
        try:
            from redis.asyncio import from_url

            self.client = from_url(self.url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
            await self.client.ping()
            self.available = True
            if event_handler:
                self._listener_task = asyncio.create_task(self._listen(event_handler))
        except Exception:
            self.available = False
            if self.client:
                await self.client.aclose()
                self.client = None

    async def close(self) -> None:
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self.client:
            await self.client.aclose()

    async def get_json(self, key: str) -> Any | None:
        namespaced = self._key("cache", key)
        if self.available and self.client:
            try:
                value = await self.client.get(namespaced)
                return json.loads(value) if value is not None else None
            except Exception:
                self.available = False
        cached = self._local_cache.get(namespaced)
        if not cached:
            return None
        expires_at, value = cached
        if expires_at is not None and expires_at <= time.monotonic():
            self._local_cache.pop(namespaced, None)
            return None
        return value

    async def set_json(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        namespaced = self._key("cache", key)
        self._local_cache[namespaced] = (time.monotonic() + ttl_seconds, value)
        if self.available and self.client:
            try:
                await self.client.set(namespaced, json.dumps(value), ex=ttl_seconds)
            except Exception:
                self.available = False

    async def allow(self, scope: str, identity: str, limit: int, window_seconds: int = 60) -> bool:
        bucket = int(time.time() // window_seconds)
        key = self._key("limit", f"{scope}:{identity}:{bucket}")
        if self.available and self.client:
            try:
                count = await self.client.incr(key)
                if count == 1:
                    await self.client.expire(key, window_seconds + 1)
                return count <= limit
            except Exception:
                self.available = False
        count, expires_at = self._local_limits.get(key, (0, time.monotonic() + window_seconds))
        if expires_at <= time.monotonic():
            count, expires_at = 0, time.monotonic() + window_seconds
        count += 1
        self._local_limits[key] = (count, expires_at)
        return count <= limit

    async def publish(self, tenant_id: str, event: dict[str, Any]) -> None:
        if not self.available or not self.client:
            return
        envelope = json.dumps({"source": self.instance_id, "tenant_id": tenant_id, "event": event}, default=str)
        try:
            await self.client.publish(self._key("events", "triage"), envelope)
        except Exception:
            self.available = False

    async def _listen(self, event_handler: EventHandler) -> None:
        assert self.client is not None
        pubsub = self.client.pubsub()
        await pubsub.subscribe(self._key("events", "triage"))
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                envelope = json.loads(message["data"])
                if envelope.get("source") != self.instance_id:
                    await event_handler(envelope["tenant_id"], envelope["event"])
        except asyncio.CancelledError:
            raise
        except Exception:
            self.available = False
        finally:
            await pubsub.aclose()

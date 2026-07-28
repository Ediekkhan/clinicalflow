from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol

import httpx


class ProviderNotConfigured(RuntimeError):
    pass


class DeliveryProvider(Protocol):
    channel: str

    async def deliver(self, *, recipient: str, payload: dict[str, Any], idempotency_key: str) -> str:
        """Deliver a redacted notification and return the provider message id."""


@dataclass(frozen=True)
class ConfiguredProvider:
    channel: str
    endpoint: str | None
    api_key: str | None

    @property
    def configured(self) -> bool:
        return bool(self.endpoint and self.api_key)

    async def deliver(self, *, recipient: str, payload: dict[str, Any], idempotency_key: str) -> str:
        if not self.configured:
            raise ProviderNotConfigured(f"{self.channel} provider is not configured")
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                self.endpoint,
                headers={"authorization": f"Bearer {self.api_key}", "idempotency-key": idempotency_key},
                json={"recipient": recipient, "payload": payload},
            )
            response.raise_for_status()
            body = response.json()
            return str(body.get("id") or body.get("message_id") or idempotency_key)


def provider_registry() -> dict[str, ConfiguredProvider]:
    return {
        channel: ConfiguredProvider(
            channel=channel,
            endpoint=os.getenv(f"{channel}_PROVIDER_URL"),
            api_key=os.getenv(f"{channel}_PROVIDER_API_KEY"),
        )
        for channel in ("EMAIL", "SMS", "PUSH", "WHATSAPP", "STORAGE")
    }


def provider_health() -> dict[str, str]:
    return {channel.lower(): "configured" if provider.configured else "not_configured" for channel, provider in provider_registry().items()}

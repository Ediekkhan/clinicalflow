from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol


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
        # Provider-specific HTTP clients belong behind this contract. Credentials are
        # read from the environment and never persisted in notifications or outbox data.
        raise NotImplementedError(f"{self.channel} provider adapter requires its provider SDK")


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

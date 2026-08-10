from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol

import httpx


class ProviderNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class HackathonSandboxProvider:
    channel: str

    @property
    def configured(self) -> bool:
        return True

    async def deliver(self, *, recipient: str, payload: dict[str, Any], idempotency_key: str) -> str:
        # The sandbox acknowledges delivery locally without contacting an external provider.
        return f"sandbox-{self.channel.lower()}-{idempotency_key}"


def provider_payload(channel: str, *, recipient: str, message: str, subject: str | None = None, sender: str | None = None) -> dict[str, Any]:
    """Build provider-shaped, minimum-necessary payloads without clinical detail."""
    channel = channel.upper()
    if channel == "SMS":
        return {"To": recipient, "From": sender, "Body": message}
    if channel == "EMAIL":
        return {"personalizations": [{"to": [{"email": recipient}]}], "from": {"email": sender or "no-reply@example.invalid"}, "subject": subject or "SynaptiVerse notification", "content": [{"type": "text/plain", "value": message}]}
    if channel == "PUSH":
        return {"message": {"token": recipient, "notification": {"title": subject or "SynaptiVerse", "body": message}}}
    if channel == "WHATSAPP":
        return {"messaging_product": "whatsapp", "to": recipient, "type": "text", "text": {"preview_url": False, "body": message}}
    if channel == "STORAGE":
        return {"object_key": recipient, "content_type": subject or "application/octet-stream"}
    raise ValueError(f"Unsupported provider channel: {channel}")


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


def provider_headers(channel: str, api_key: str) -> dict[str, str]:
    """Return common auth headers; provider-specific endpoints can override them."""
    if channel.upper() == "SMS":
        return {"authorization": f"Basic {api_key}"}
    if channel.upper() == "WHATSAPP":
        return {"authorization": f"Bearer {api_key}"}
    return {"authorization": f"Bearer {api_key}"}


def provider_registry() -> dict[str, ConfiguredProvider | HackathonSandboxProvider]:
    if os.getenv("APP_ENV", "").strip().lower() == "hackathon" and os.getenv("ENABLE_HACKATHON_PROVIDERS", "false").lower() == "true":
        return {channel: HackathonSandboxProvider(channel) for channel in ("EMAIL", "SMS", "PUSH", "WHATSAPP", "STORAGE")}
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

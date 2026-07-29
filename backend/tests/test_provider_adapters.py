import asyncio
import pytest

from app.services.provider_adapters import ConfiguredProvider, ProviderNotConfigured, provider_payload


def test_unconfigured_provider_fails_closed() -> None:
    provider = ConfiguredProvider("EMAIL", None, None)
    with pytest.raises(ProviderNotConfigured):
        asyncio.run(provider.deliver(recipient="patient@example.org", payload={"body": "Safe notification"}, idempotency_key="event-1"))


def test_provider_health_reports_configuration_without_exposing_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMAIL_PROVIDER_URL", "https://provider.invalid/send")
    monkeypatch.setenv("EMAIL_PROVIDER_API_KEY", "secret-value")
    from app.services.provider_adapters import provider_health

    health = provider_health()
    assert health["email"] == "configured"
    assert "secret-value" not in str(health)


@pytest.mark.parametrize(
    ("channel", "expected"),
    [("SMS", "Body"), ("EMAIL", "personalizations"), ("PUSH", "message"), ("WHATSAPP", "messaging_product")],
)
def test_provider_payloads_are_channel_specific(channel: str, expected: str) -> None:
    payload = provider_payload(channel, recipient="recipient", message="Your appointment is confirmed", subject="Update")
    assert expected in payload
    assert "diagnosis" not in str(payload).lower()

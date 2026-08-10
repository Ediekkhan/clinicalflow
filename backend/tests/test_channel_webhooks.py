import hashlib
import hmac
import json
import secrets

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def signature(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_signed_sms_webhook_creates_ticket_and_accepts_delivery_receipt() -> None:
    previous = settings.channel_webhook_secret
    settings.channel_webhook_secret = "test-webhook-secret"
    try:
        phone = f"+23480{secrets.randbelow(100_000_000):08d}"
        inbound = json.dumps({"from": phone, "text": "I have fever and weakness", "message_id": "sms-in-1"}, separators=(",", ":")).encode()
        receipt = json.dumps({"message_id": "sms-in-1", "status": "delivered"}, separators=(",", ":")).encode()
        with TestClient(app) as client:
            response = client.post("/api/v1/webhooks/sms", content=inbound, headers={"x-clinicalflow-signature": signature(inbound, settings.channel_webhook_secret), "content-type": "application/json"})
            delivery = client.post("/api/v1/webhooks/sms", content=receipt, headers={"x-clinicalflow-signature": signature(receipt, settings.channel_webhook_secret), "content-type": "application/json"})
            rejected = client.post("/api/v1/webhooks/sms", content=inbound, headers={"x-clinicalflow-signature": "sha256=wrong", "content-type": "application/json"})
    finally:
        settings.channel_webhook_secret = previous

    assert response.status_code == 200
    assert response.json()["reply"]["action"] == "TICKET_CREATED"
    assert delivery.json()["delivery_status"] == "DELIVERED"
    assert rejected.status_code == 401


def test_channel_templates_are_available_for_low_bandwidth_delivery() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/channels/templates")
    assert response.status_code == 200
    assert {template["id"] for template in response.json()["sms"]} == {"queue", "booking", "cancellation"}

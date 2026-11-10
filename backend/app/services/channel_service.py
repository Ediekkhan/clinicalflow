from __future__ import annotations

import hashlib
import hmac
from typing import Any


SMS_TEMPLATES = {
    "queue": "ClinicalFlow: Ticket {ticket_number}. Urgency {urgency}. Reply BOOK for slots or CANCEL to cancel.",
    "booking": "ClinicalFlow: {ticket_number} booked for {date}. Reply CANCEL to cancel.",
    "cancellation": "ClinicalFlow: Appointment cancelled. Reply BOOK to reschedule.",
}


def valid_signature(body: bytes, signature: str | None, secret: str) -> bool:
    if not signature or not secret or secret == "change-me":
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def normalize_webhook(channel: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize the MVP adapter contract and common Meta-style fields."""
    if payload.get("message_id") and payload.get("status"):
        return payload
    if "from" in payload:
        return payload
    if channel == "whatsapp":
        try:
            value = payload["entry"][0]["changes"][0]["value"]
            if value.get("statuses"):
                status = value["statuses"][0]
                return {"message_id": status["id"], "status": status["status"]}
            message = value["messages"][0]
            text = message.get("text", {}).get("body") or message.get("button", {}).get("payload") or ""
            return {"from": message["from"], "text": text, "message_id": message.get("id")}
        except (KeyError, IndexError, TypeError):
            pass
    raise ValueError("Unsupported provider payload")


def intent_from_text(text: str) -> str | None:
    normalized = text.strip().upper()
    return {"1": "CONTINUE_EXISTING", "2": "REGISTER_NEW_PATIENT", "3": "BOOK_APPOINTMENT", "BOOK": "BOOK_APPOINTMENT", "CANCEL": "CANCEL_APPOINTMENT"}.get(normalized)

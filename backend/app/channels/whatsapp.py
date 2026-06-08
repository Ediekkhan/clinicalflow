from datetime import datetime

from app.models.domain import ProviderSlot, Ticket


def duplicate_identity_menu(phone: str, active_ticket_numbers: list[str]) -> dict[str, object]:
    return {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "Existing visit found"},
            "body": {
                "text": (
                    "This phone already has an active clinic visit: "
                    f"{', '.join(active_ticket_numbers)}. Choose what you want to do."
                )
            },
            "action": {
                "button": "Select visit intent",
                "sections": [
                    {
                        "title": "Shared phone options",
                        "rows": [
                            {
                                "id": "continue_existing",
                                "title": "Continue existing visit",
                                "description": "Use the active queue ticket on this phone.",
                            },
                            {
                                "id": "register_new_patient",
                                "title": "Register a new patient",
                                "description": "Create a separate ticket under this phone group.",
                            },
                        ],
                    }
                ],
            },
        },
    }


def slot_list_template(phone: str, slots: list[ProviderSlot]) -> dict[str, object]:
    rows = [
        {
            "id": str(slot.id),
            "title": f"{slot.starts_at:%a %I:%M %p}",
            "description": f"{slot.specialty} with {slot.provider_name} in {slot.room_label}",
        }
        for slot in slots[:10]
    ]
    return {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "Available appointment times"},
            "body": {"text": "Choose the clinic slot that works best for you."},
            "action": {"button": "View slots", "sections": [{"title": "Open slots", "rows": rows}]},
        },
    }


def dangerous_keyword_alert(phone: str) -> dict[str, object]:
    return {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {
            "body": (
                "RED ALERT: Your message may describe an emergency. "
                "Please go to the emergency desk immediately or call local emergency services."
            )
        },
    }


def booking_confirmation(ticket: Ticket, slot_start: datetime) -> dict[str, object]:
    return {
        "messaging_product": "whatsapp",
        "to": ticket.customer_phone,
        "type": "text",
        "text": {
            "body": (
                f"Booking confirmed for {ticket.ticket_number}: "
                f"{slot_start:%A %d %b, %I:%M %p}. Reply CANCEL if you need to cancel."
            )
        },
    }


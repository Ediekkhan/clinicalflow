from datetime import datetime


def queue_assignment(ticket_number: str, urgency: str, room_hint: str = "front desk") -> str:
    return (
        f"[PROJECT_NAME]: Ticket {ticket_number}. Urgency: {urgency}. "
        f"Please wait near {room_hint}. Reply CANCEL to cancel an appointment."
    )[:160]


def booking_confirmation(ticket_number: str, starts_at: datetime) -> str:
    return (
        f"[PROJECT_NAME]: {ticket_number} booked for {starts_at:%d/%m %I:%M%p}. "
        "Reply CANCEL to cancel."
    )[:160]


def shift_alert(ticket_number: str, starts_at: datetime) -> str:
    return (
        f"[PROJECT_NAME]: Your appointment {ticket_number} shifted to "
        f"{starts_at:%d/%m %I:%M%p}. Please arrive 10 mins early."
    )[:160]


def cancellation_confirmed(ticket_number: str) -> str:
    return f"[PROJECT_NAME]: Appointment for {ticket_number} cancelled. Reply BOOK to reschedule."[:160]


from uuid import UUID

from pydantic import BaseModel


class AppointmentCreateSchema(BaseModel):
    ticket_id: UUID
    provider_slot_id: UUID
    channel_origin: str = "WEB"

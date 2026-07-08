from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_patient
from app.db.session import get_session
from app.models.domain import Appointment, AuditLog, Patient, Ticket
from app.schemas.patient import DeletionRequestSchema
from app.services.audit_service import AuditAction, write_audit_log


router = APIRouter(prefix="/patient/my-data", tags=["compliance"])


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/export")
async def export_my_data(
    request: Request,
    current_patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_session),
) -> JSONResponse:
    tickets = (
        await db.scalars(
            select(Ticket)
            .where(Ticket.patient_id == current_patient.id)
            .order_by(Ticket.created_at.desc())
        )
    ).all()
    appointments = (
        await db.scalars(
            select(Appointment)
            .where(Appointment.patient_id == current_patient.id)
            .order_by(Appointment.created_at.desc())
        )
    ).all()
    audit_logs = (
        await db.scalars(
            select(AuditLog)
            .where(AuditLog.actor_id == current_patient.id)
            .order_by(AuditLog.timestamp.desc())
        )
    ).all()
    data = {
        "export_generated_at": datetime.now(UTC).isoformat(),
        "patient_profile": {
            "id": current_patient.id,
            "tenant_id": current_patient.tenant_id,
            "full_name": current_patient.full_name,
            "phone": current_patient.phone,
            "date_of_birth": current_patient.date_of_birth,
            "gender": current_patient.gender,
            "card_number": current_patient.card_number,
            "created_at": current_patient.created_at,
        },
        "triage_history": tickets,
        "appointments": appointments,
        "activity_log": audit_logs,
    }
    await write_audit_log(
        db=db,
        action=AuditAction.DATA_EXPORTED,
        actor_id=str(current_patient.id),
        actor_type="PATIENT",
        tenant_id=str(current_patient.tenant_id),
        ip_address=_client_ip(request),
        metadata={"export_type": "FULL_DATA_EXPORT"},
        user_agent=request.headers.get("user-agent"),
    )
    return JSONResponse(content=jsonable_encoder(data))


@router.post("/delete-request")
async def request_data_deletion(
    request: Request,
    body: DeletionRequestSchema,
    current_patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_session),
) -> JSONResponse:
    current_patient.pending_deletion = True
    await write_audit_log(
        db=db,
        action=AuditAction.DATA_DELETION_REQUEST,
        actor_id=str(current_patient.id),
        actor_type="PATIENT",
        tenant_id=str(current_patient.tenant_id),
        ip_address=_client_ip(request),
        metadata={"reason": body.reason},
        user_agent=request.headers.get("user-agent"),
    )
    return JSONResponse(
        content={
            "message": "Deletion request received. You will be contacted within 30 days."
        }
    )

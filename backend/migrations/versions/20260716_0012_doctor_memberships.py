"""Add hospital doctor memberships and appointment assignment fields.

Revision ID: 20260716_0012
Revises: 20260716_0011
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260716_0012"
down_revision: str | None = "20260716_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "hospital_doctor_memberships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("hospital_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("doctor_id", sa.Uuid(), sa.ForeignKey("auth_accounts.id"), nullable=False),
        sa.Column("specialty_id", sa.String(128), nullable=False),
        sa.Column("verification_status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("employment_status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("notification_preferences", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("active_from", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("active_until", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("hospital_id", "doctor_id", "specialty_id", name="uq_hospital_doctor_specialty"),
    )
    op.create_index("ix_hospital_doctor_memberships_hospital_specialty", "hospital_doctor_memberships", ["hospital_id", "specialty_id"])
    op.create_index("ix_hospital_doctor_memberships_doctor", "hospital_doctor_memberships", ["doctor_id"])

    op.add_column("providers", sa.Column("doctor_id", sa.Uuid(), nullable=True))
    op.add_column("providers", sa.Column("max_daily_capacity", sa.Integer(), nullable=False, server_default="12"))
    op.create_index("ix_providers_doctor_id", "providers", ["doctor_id"])

    for column in (
        sa.Column("hospital_id", sa.Uuid(), nullable=True),
        sa.Column("doctor_id", sa.Uuid(), nullable=True),
        sa.Column("specialty_id", sa.String(128), nullable=True),
        sa.Column("urgency", sa.String(32), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
    ):
        op.add_column("appointments", column)
    op.execute("UPDATE appointments SET hospital_id = tenant_id WHERE hospital_id IS NULL")
    op.create_index("ix_appointments_hospital_id", "appointments", ["hospital_id"])
    op.create_index("ix_appointments_doctor_id", "appointments", ["doctor_id"])
    op.create_index("ix_appointments_specialty_id", "appointments", ["specialty_id"])
    op.create_index("ix_appointments_hospital_doctor", "appointments", ["hospital_id", "doctor_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("recipient_account_id", sa.Uuid(), nullable=True),
        sa.Column("recipient_role", sa.String(32), nullable=False),
        sa.Column("appointment_id", sa.Uuid(), nullable=True),
        sa.Column("ticket_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_tenant_recipient", "notifications", ["tenant_id", "recipient_account_id"])
    op.create_index("ix_notifications_appointment", "notifications", ["appointment_id"])


def downgrade() -> None:
    op.drop_index("ix_notifications_appointment", table_name="notifications")
    op.drop_index("ix_notifications_tenant_recipient", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_appointments_hospital_doctor", table_name="appointments")
    op.drop_index("ix_appointments_specialty_id", table_name="appointments")
    op.drop_index("ix_appointments_doctor_id", table_name="appointments")
    op.drop_index("ix_appointments_hospital_id", table_name="appointments")
    for column_name in ("ends_at", "starts_at", "urgency", "specialty_id", "doctor_id", "hospital_id"):
        op.drop_column("appointments", column_name)

    op.drop_index("ix_providers_doctor_id", table_name="providers")
    op.drop_column("providers", "max_daily_capacity")
    op.drop_column("providers", "doctor_id")

    op.drop_index("ix_hospital_doctor_memberships_doctor", table_name="hospital_doctor_memberships")
    op.drop_index("ix_hospital_doctor_memberships_hospital_specialty", table_name="hospital_doctor_memberships")
    op.drop_table("hospital_doctor_memberships")
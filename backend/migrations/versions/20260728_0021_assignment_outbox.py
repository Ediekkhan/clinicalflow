"""Add assignment requests, notification acknowledgement, and outbox events.

Revision ID: 20260728_0021
Revises: 20260728_0020
"""
from collections.abc import Sequence

from alembic import context, op
import sqlalchemy as sa

revision: str = "20260728_0021"
down_revision: str | None = "20260728_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("notifications") as batch:
        batch.add_column(sa.Column("acknowledged_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("acknowledged_by_account_id", sa.Uuid()))
        batch.create_foreign_key("fk_notification_acknowledged_by", "auth_accounts", ["acknowledged_by_account_id"], ["id"])
    op.create_table(
        "appointment_assignment_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("hospital_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("department_id", sa.String(128), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("tickets.id"), nullable=False),
        sa.Column("appointment_id", sa.Uuid(), sa.ForeignKey("appointments.id")),
        sa.Column("recipient_user_id", sa.Uuid(), sa.ForeignKey("auth_accounts.id")),
        sa.Column("recipient_membership_id", sa.Uuid(), sa.ForeignKey("staff_memberships.id")),
        sa.Column("specialty_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="OPEN"),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("ticket_id", "recipient_membership_id", name="uq_assignment_request_ticket_membership"),
    )
    op.create_index("ix_assignment_requests_recipient_status", "appointment_assignment_requests", ["recipient_user_id", "status", "expires_at"])
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("aggregate_type", sa.String(64), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("recipient_user_id", sa.Uuid(), sa.ForeignKey("auth_accounts.id")),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("classification", sa.String(32), nullable=False, server_default="RESTRICTED"),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_outbox_events_delivery", "outbox_events", ["status", "available_at", "created_at"])
    for table in ("appointment_assignment_requests", "outbox_events"):
        if context.is_offline_mode() or op.get_bind().dialect.name == "postgresql":
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_outbox_events_delivery", table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_index("ix_assignment_requests_recipient_status", table_name="appointment_assignment_requests")
    op.drop_table("appointment_assignment_requests")
    with op.batch_alter_table("notifications") as batch:
        batch.drop_constraint("fk_notification_acknowledged_by", type_="foreignkey")
        batch.drop_column("acknowledged_by_account_id")
        batch.drop_column("acknowledged_at")

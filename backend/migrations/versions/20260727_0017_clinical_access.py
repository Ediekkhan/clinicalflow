"""Add treatment access and notification delivery records.

Revision ID: 20260727_0017
Revises: 20260727_0016
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260727_0017"
down_revision: str | None = "20260727_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("notification_deliveries", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("notification_id", sa.Uuid(), sa.ForeignKey("notifications.id"), nullable=False), sa.Column("channel", sa.String(32), nullable=False), sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"), sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"), sa.Column("last_error", sa.Text()), sa.Column("next_attempt_at", sa.DateTime(timezone=True)), sa.Column("delivered_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_notification_deliveries_notification_id", "notification_deliveries", ["notification_id"])
    op.create_index("ix_notification_deliveries_retry", "notification_deliveries", ["status", "next_attempt_at"])
    op.create_table("care_team_assignments", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("hospital_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False), sa.Column("department_id", sa.String(128), nullable=False), sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("tickets.id"), nullable=False), sa.Column("appointment_id", sa.Uuid(), sa.ForeignKey("appointments.id")), sa.Column("user_id", sa.Uuid(), sa.ForeignKey("auth_accounts.id"), nullable=False), sa.Column("membership_id", sa.Uuid(), sa.ForeignKey("staff_memberships.id"), nullable=False), sa.Column("assignment_type", sa.String(32), nullable=False), sa.Column("permitted_sections_json", sa.Text()), sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"), sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("ends_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_care_team_assignments_ticket_user", "care_team_assignments", ["ticket_id", "user_id", "status"])
    op.create_index("ix_care_team_assignments_membership", "care_team_assignments", ["membership_id", "status"])
    op.create_table("break_glass_grants", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("hospital_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False), sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("tickets.id"), nullable=False), sa.Column("user_id", sa.Uuid(), sa.ForeignKey("auth_accounts.id"), nullable=False), sa.Column("membership_id", sa.Uuid(), sa.ForeignKey("staff_memberships.id"), nullable=False), sa.Column("reason", sa.Text(), nullable=False), sa.Column("confirmed", sa.Boolean(), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("revoked_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_break_glass_grants_ticket_membership", "break_glass_grants", ["ticket_id", "membership_id", "expires_at"])
    if op.get_bind().dialect.name == "postgresql":
        for table in ("notification_deliveries", "care_team_assignments", "break_glass_grants"):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_break_glass_grants_ticket_membership", table_name="break_glass_grants")
    op.drop_table("break_glass_grants")
    op.drop_index("ix_care_team_assignments_membership", table_name="care_team_assignments")
    op.drop_index("ix_care_team_assignments_ticket_user", table_name="care_team_assignments")
    op.drop_table("care_team_assignments")
    op.drop_index("ix_notification_deliveries_retry", table_name="notification_deliveries")
    op.drop_index("ix_notification_deliveries_notification_id", table_name="notification_deliveries")
    op.drop_table("notification_deliveries")
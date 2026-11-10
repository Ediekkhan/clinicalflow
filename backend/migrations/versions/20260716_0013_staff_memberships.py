"""Add staff memberships and membership-scoped notifications.

Revision ID: 20260716_0013
Revises: 20260716_0012
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260716_0013"
down_revision: str | None = "20260716_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "staff_memberships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("auth_accounts.id"), nullable=False),
        sa.Column("hospital_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("department_id", sa.String(128), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("specialty_id", sa.String(128), nullable=True),
        sa.Column("professional_license_number", sa.String(128), nullable=True),
        sa.Column("verification_status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("employment_status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("notification_preferences", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_on_duty", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("active_from", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("active_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "hospital_id", "department_id", "role", name="uq_staff_membership_workspace_role"),
    )
    op.create_index("ix_staff_memberships_user", "staff_memberships", ["user_id"])
    op.create_index("ix_staff_memberships_hospital_department", "staff_memberships", ["hospital_id", "department_id"])
    op.create_index("ix_staff_memberships_assignment", "staff_memberships", ["hospital_id", "department_id", "specialty_id", "role"])

    op.create_table(
        "staff_invitations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("hospital_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("department_id", sa.String(128), nullable=False),
        sa.Column("permitted_role", sa.String(32), nullable=False),
        sa.Column("invitation_code", sa.String(128), nullable=False),
        sa.Column("invited_email", sa.String(255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_account_id", sa.Uuid(), sa.ForeignKey("auth_accounts.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("invitation_code", name="uq_staff_invitations_code"),
    )
    op.create_index("ix_staff_invitations_hospital_department", "staff_invitations", ["hospital_id", "department_id"])

    op.add_column("auth_sessions", sa.Column("selected_membership_id", sa.Uuid(), nullable=True))
    op.create_index("ix_auth_sessions_selected_membership_id", "auth_sessions", ["selected_membership_id"])

    op.add_column("appointments", sa.Column("department_id", sa.String(128), nullable=True))
    op.add_column("appointments", sa.Column("staff_membership_id", sa.Uuid(), nullable=True))
    op.create_index("ix_appointments_department_id", "appointments", ["department_id"])
    op.create_index("ix_appointments_staff_membership_id", "appointments", ["staff_membership_id"])

    for column in (
        sa.Column("recipient_user_id", sa.Uuid(), nullable=True),
        sa.Column("recipient_membership_id", sa.Uuid(), nullable=True),
        sa.Column("hospital_id", sa.Uuid(), nullable=True),
        sa.Column("department_id", sa.String(128), nullable=True),
        sa.Column("priority", sa.String(32), nullable=False, server_default="NORMAL"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    ):
        op.add_column("notifications", column)
    op.execute("UPDATE notifications SET recipient_user_id = recipient_account_id WHERE recipient_user_id IS NULL")
    op.execute("UPDATE notifications SET hospital_id = tenant_id WHERE hospital_id IS NULL")
    op.create_index("ix_notifications_recipient_user", "notifications", ["recipient_user_id"])
    op.create_index("ix_notifications_recipient_membership", "notifications", ["recipient_membership_id"])
    op.create_index("ix_notifications_workspace", "notifications", ["hospital_id", "department_id"])

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in ("staff_memberships", "staff_invitations"):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"CREATE POLICY tenant_isolation_policy ON {table} USING (hospital_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) WITH CHECK (hospital_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)")


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_selected_membership_id", table_name="auth_sessions")
    op.drop_column("auth_sessions", "selected_membership_id")

    op.drop_index("ix_notifications_workspace", table_name="notifications")
    op.drop_index("ix_notifications_recipient_membership", table_name="notifications")
    op.drop_index("ix_notifications_recipient_user", table_name="notifications")
    for column_name in ("read_at", "priority", "department_id", "hospital_id", "recipient_membership_id", "recipient_user_id"):
        op.drop_column("notifications", column_name)

    op.drop_index("ix_appointments_staff_membership_id", table_name="appointments")
    op.drop_index("ix_appointments_department_id", table_name="appointments")
    op.drop_column("appointments", "staff_membership_id")
    op.drop_column("appointments", "department_id")

    op.drop_index("ix_staff_invitations_hospital_department", table_name="staff_invitations")
    op.drop_table("staff_invitations")

    op.drop_index("ix_staff_memberships_assignment", table_name="staff_memberships")
    op.drop_index("ix_staff_memberships_hospital_department", table_name="staff_memberships")
    op.drop_index("ix_staff_memberships_user", table_name="staff_memberships")
    op.drop_table("staff_memberships")


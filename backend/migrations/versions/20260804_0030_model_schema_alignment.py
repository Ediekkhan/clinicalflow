"""Align persisted constraints and indexes with the application models.

Revision ID: 20260804_0030
Revises: 20260803_0029
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260804_0030"
down_revision: str | None = "20260803_0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing rows were populated from tenant_id when the routing fields were
    # introduced. Repeat the backfill defensively before enforcing the model's
    # non-null invariant.
    op.execute("UPDATE appointments SET hospital_id = tenant_id WHERE hospital_id IS NULL")

    with op.batch_alter_table("appointments") as batch:
        batch.alter_column("hospital_id", existing_type=sa.Uuid(), nullable=False)
        batch.create_foreign_key(
            "fk_appointments_hospital_id_tenants", "tenants", ["hospital_id"], ["id"]
        )
        batch.create_foreign_key(
            "fk_appointments_doctor_id_auth_accounts", "auth_accounts", ["doctor_id"], ["id"]
        )
        batch.create_foreign_key(
            "fk_appointments_staff_membership_id_staff_memberships",
            "staff_memberships",
            ["staff_membership_id"],
            ["id"],
        )

    with op.batch_alter_table("auth_sessions") as batch:
        batch.create_foreign_key(
            "fk_auth_sessions_selected_membership_id_staff_memberships",
            "staff_memberships",
            ["selected_membership_id"],
            ["id"],
        )

    with op.batch_alter_table("notifications") as batch:
        batch.drop_index("ix_notifications_recipient_membership")
        batch.drop_index("ix_notifications_recipient_user")
        batch.drop_index("ix_notifications_workspace")
        batch.create_foreign_key(
            "fk_notifications_recipient_membership_id_staff_memberships",
            "staff_memberships",
            ["recipient_membership_id"],
            ["id"],
        )
        batch.create_foreign_key(
            "fk_notifications_recipient_user_id_auth_accounts",
            "auth_accounts",
            ["recipient_user_id"],
            ["id"],
        )
        batch.create_foreign_key(
            "fk_notifications_recipient_account_id_auth_accounts",
            "auth_accounts",
            ["recipient_account_id"],
            ["id"],
        )
        batch.create_foreign_key(
            "fk_notifications_ticket_id_tickets", "tickets", ["ticket_id"], ["id"]
        )
        batch.create_foreign_key(
            "fk_notifications_appointment_id_appointments",
            "appointments",
            ["appointment_id"],
            ["id"],
        )
        batch.create_foreign_key(
            "fk_notifications_hospital_id_tenants", "tenants", ["hospital_id"], ["id"]
        )

    with op.batch_alter_table("providers") as batch:
        batch.create_foreign_key(
            "fk_providers_doctor_id_auth_accounts", "auth_accounts", ["doctor_id"], ["id"]
        )

    with op.batch_alter_table("staff_invitations") as batch:
        batch.create_foreign_key(
            "fk_staff_invitations_invited_by_auth_accounts",
            "auth_accounts",
            ["invited_by"],
            ["id"],
        )
        batch.create_foreign_key(
            "fk_staff_invitations_organization_id_tenants",
            "tenants",
            ["organization_id"],
            ["id"],
        )

    with op.batch_alter_table("tickets") as batch:
        batch.create_foreign_key(
            "fk_tickets_routed_tenant_id_tenants", "tenants", ["routed_tenant_id"], ["id"]
        )

    op.create_index(
        "ix_facility_verification_cases_assigned_reviewer_id",
        "facility_verification_cases",
        ["assigned_reviewer_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_facility_verification_cases_assigned_reviewer_id",
        table_name="facility_verification_cases",
    )

    with op.batch_alter_table("tickets") as batch:
        batch.drop_constraint("fk_tickets_routed_tenant_id_tenants", type_="foreignkey")

    with op.batch_alter_table("staff_invitations") as batch:
        batch.drop_constraint(
            "fk_staff_invitations_organization_id_tenants", type_="foreignkey"
        )
        batch.drop_constraint(
            "fk_staff_invitations_invited_by_auth_accounts", type_="foreignkey"
        )

    with op.batch_alter_table("providers") as batch:
        batch.drop_constraint("fk_providers_doctor_id_auth_accounts", type_="foreignkey")

    with op.batch_alter_table("notifications") as batch:
        for constraint in (
            "fk_notifications_hospital_id_tenants",
            "fk_notifications_appointment_id_appointments",
            "fk_notifications_ticket_id_tickets",
            "fk_notifications_recipient_account_id_auth_accounts",
            "fk_notifications_recipient_user_id_auth_accounts",
            "fk_notifications_recipient_membership_id_staff_memberships",
        ):
            batch.drop_constraint(constraint, type_="foreignkey")
        batch.create_index("ix_notifications_recipient_membership", ["recipient_membership_id"])
        batch.create_index("ix_notifications_recipient_user", ["recipient_user_id"])
        batch.create_index("ix_notifications_workspace", ["hospital_id", "department_id"])

    with op.batch_alter_table("auth_sessions") as batch:
        batch.drop_constraint(
            "fk_auth_sessions_selected_membership_id_staff_memberships", type_="foreignkey"
        )

    with op.batch_alter_table("appointments") as batch:
        batch.drop_constraint(
            "fk_appointments_staff_membership_id_staff_memberships", type_="foreignkey"
        )
        batch.drop_constraint(
            "fk_appointments_doctor_id_auth_accounts", type_="foreignkey"
        )
        batch.drop_constraint("fk_appointments_hospital_id_tenants", type_="foreignkey")
        batch.alter_column("hospital_id", existing_type=sa.Uuid(), nullable=True)

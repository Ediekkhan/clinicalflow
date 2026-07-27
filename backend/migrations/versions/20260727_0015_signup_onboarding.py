"""Add role-specific signup onboarding records.

Revision ID: 20260727_0015
Revises: 20260716_0014
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260727_0015"
down_revision: str | None = "20260716_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("staff_invitations", sa.Column("token_hash", sa.String(64), nullable=True))
    op.add_column("staff_invitations", sa.Column("organization_id", sa.Uuid(), nullable=True))
    op.add_column("staff_invitations", sa.Column("invited_phone", sa.String(32), nullable=True))
    op.add_column("staff_invitations", sa.Column("intended_role", sa.String(32), nullable=True))
    op.add_column("staff_invitations", sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("staff_invitations", sa.Column("invited_by", sa.Uuid(), nullable=True))
    op.create_index("ix_staff_invitations_token_hash", "staff_invitations", ["token_hash"], unique=True)

    op.create_table(
        "signup_applications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("reference", sa.String(32), nullable=False, unique=True),
        sa.Column("application_type", sa.String(32), nullable=False),
        sa.Column("onboarding_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("country", sa.String(128), nullable=False),
        sa.Column("organization_name", sa.String(255), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=True),
        sa.Column("invitation_id", sa.Uuid(), sa.ForeignKey("staff_invitations.id"), nullable=True),
        sa.Column("account_id", sa.Uuid(), sa.ForeignKey("auth_accounts.id"), nullable=True),
        sa.Column("consent_version", sa.String(32), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_signup_applications_reference", "signup_applications", ["reference"], unique=True)
    op.create_index("ix_signup_applications_type_status", "signup_applications", ["application_type", "status"])
    op.create_index("ix_signup_applications_email", "signup_applications", ["email"])
    op.create_index("ix_signup_applications_phone", "signup_applications", ["phone"])

    op.create_table(
        "organization_applications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("signup_application_id", sa.Uuid(), sa.ForeignKey("signup_applications.id"), nullable=False, unique=True),
        sa.Column("legal_name", sa.String(255), nullable=False),
        sa.Column("registration_number", sa.String(128), nullable=True),
        sa.Column("licence_number", sa.String(128), nullable=True),
        sa.Column("regulatory_authority", sa.String(255), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("verification_status", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_organization_applications_status", "organization_applications", ["verification_status"])

    op.create_table(
        "professional_credentials",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("signup_application_id", sa.Uuid(), sa.ForeignKey("signup_applications.id"), nullable=False),
        sa.Column("licence_number", sa.String(128), nullable=False),
        sa.Column("licensing_authority", sa.String(255), nullable=False),
        sa.Column("jurisdiction", sa.String(128), nullable=False),
        sa.Column("specialty", sa.String(128), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_status", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("licence_number", "jurisdiction", name="uq_professional_credential_jurisdiction"),
    )
    op.create_index("ix_professional_credentials_application", "professional_credentials", ["signup_application_id"])

    op.create_table(
        "verification_documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("signup_application_id", sa.Uuid(), sa.ForeignKey("signup_applications.id"), nullable=False),
        sa.Column("document_type", sa.String(64), nullable=False),
        sa.Column("private_storage_key", sa.String(512), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("verification_status", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_verification_documents_application", "verification_documents", ["signup_application_id"])

    op.create_table(
        "consent_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("signup_application_id", sa.Uuid(), sa.ForeignKey("signup_applications.id"), nullable=False),
        sa.Column("account_id", sa.Uuid(), sa.ForeignKey("auth_accounts.id"), nullable=True),
        sa.Column("consent_type", sa.String(64), nullable=False),
        sa.Column("policy_version", sa.String(32), nullable=False),
        sa.Column("accepted", sa.Boolean(), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_consent_records_application", "consent_records", ["signup_application_id"])

    op.create_table(
        "application_review_history",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("signup_application_id", sa.Uuid(), sa.ForeignKey("signup_applications.id"), nullable=False),
        sa.Column("reviewer_account_id", sa.Uuid(), sa.ForeignKey("auth_accounts.id"), nullable=True),
        sa.Column("previous_status", sa.String(64), nullable=True),
        sa.Column("new_status", sa.String(64), nullable=False),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_application_review_history_application", "application_review_history", ["signup_application_id", "created_at"])

    op.create_table(
        "verification_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("signup_application_id", sa.Uuid(), sa.ForeignKey("signup_applications.id"), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_verification_events_application_type", "verification_events", ["signup_application_id", "event_type"])

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in ("signup_applications", "organization_applications", "professional_credentials", "verification_documents", "consent_records", "application_review_history", "verification_events"):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    for index_name, table_name in (
        ("ix_verification_events_application_type", "verification_events"),
        ("ix_application_review_history_application", "application_review_history"),
        ("ix_consent_records_application", "consent_records"),
        ("ix_verification_documents_application", "verification_documents"),
        ("ix_professional_credentials_application", "professional_credentials"),
        ("ix_organization_applications_status", "organization_applications"),
    ):
        op.drop_index(index_name, table_name=table_name)
        op.drop_table(table_name)
    op.drop_index("ix_signup_applications_phone", table_name="signup_applications")
    op.drop_index("ix_signup_applications_email", table_name="signup_applications")
    op.drop_index("ix_signup_applications_type_status", table_name="signup_applications")
    op.drop_index("ix_signup_applications_reference", table_name="signup_applications")
    op.drop_table("signup_applications")
    op.drop_index("ix_staff_invitations_token_hash", table_name="staff_invitations")
    for column in ("invited_by", "revoked_at", "intended_role", "invited_phone", "organization_id", "token_hash"):
        op.drop_column("staff_invitations", column)
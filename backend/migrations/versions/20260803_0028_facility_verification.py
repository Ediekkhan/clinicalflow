"""facility verification cases, registry checks, findings, and activation records"""
from alembic import op
import sqlalchemy as sa

revision = "20260803_0028"
down_revision = "20260731_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = sa.Uuid()
    op.create_table(
        "facility_verification_cases",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("signup_application_id", uuid, sa.ForeignKey("signup_applications.id"), nullable=False),
        sa.Column("organization_application_id", uuid, sa.ForeignKey("organization_applications.id"), nullable=False),
        sa.Column("status", sa.String(64), nullable=False), sa.Column("priority", sa.String(32), nullable=False),
        sa.Column("assigned_reviewer_id", uuid, sa.ForeignKey("auth_accounts.id")),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("review_due_at", sa.DateTime(timezone=True)),
        sa.Column("last_transition_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)), sa.Column("resolved_by_id", uuid, sa.ForeignKey("auth_accounts.id")),
        sa.Column("government_check_status", sa.String(32), nullable=False),
        sa.Column("risk_flags_json", sa.Text()), sa.Column("reviewer_notes", sa.Text()),
        sa.UniqueConstraint("signup_application_id", name="uq_facility_verification_case_application"),
    )
    op.create_index("ix_facility_verification_cases_queue", "facility_verification_cases", ["status", "review_due_at", "priority"])
    op.create_table(
        "external_registry_checks",
        sa.Column("id", uuid, primary_key=True), sa.Column("verification_case_id", uuid, sa.ForeignKey("facility_verification_cases.id"), nullable=False),
        sa.Column("registry_code", sa.String(64), nullable=False), sa.Column("query_reference", sa.String(255)), sa.Column("result", sa.String(32), nullable=False),
        sa.Column("matched_name", sa.String(255)), sa.Column("response_json", sa.Text()), sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)), sa.Column("checked_by_id", uuid, sa.ForeignKey("auth_accounts.id")),
    )
    op.create_index("ix_external_registry_checks_case", "external_registry_checks", ["verification_case_id", "checked_at"])
    op.create_table(
        "verification_findings",
        sa.Column("id", uuid, primary_key=True), sa.Column("verification_case_id", uuid, sa.ForeignKey("facility_verification_cases.id"), nullable=False),
        sa.Column("category", sa.String(64), nullable=False), sa.Column("severity", sa.String(32), nullable=False), sa.Column("status", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False), sa.Column("resolution", sa.Text()), sa.Column("created_by_id", uuid, sa.ForeignKey("auth_accounts.id")),
        sa.Column("resolved_by_id", uuid, sa.ForeignKey("auth_accounts.id")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_verification_findings_case_status", "verification_findings", ["verification_case_id", "status"])
    op.create_table(
        "facility_admin_activations",
        sa.Column("id", uuid, primary_key=True), sa.Column("verification_case_id", uuid, sa.ForeignKey("facility_verification_cases.id"), nullable=False),
        sa.Column("account_id", uuid, sa.ForeignKey("auth_accounts.id"), nullable=False), sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("used_at", sa.DateTime(timezone=True)), sa.Column("revoked_at", sa.DateTime(timezone=True)), sa.Column("activated_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_facility_admin_activations_token", "facility_admin_activations", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_facility_admin_activations_token", table_name="facility_admin_activations")
    op.drop_table("facility_admin_activations")
    op.drop_index("ix_verification_findings_case_status", table_name="verification_findings")
    op.drop_table("verification_findings")
    op.drop_index("ix_external_registry_checks_case", table_name="external_registry_checks")
    op.drop_table("external_registry_checks")
    op.drop_index("ix_facility_verification_cases_queue", table_name="facility_verification_cases")
    op.drop_table("facility_verification_cases")

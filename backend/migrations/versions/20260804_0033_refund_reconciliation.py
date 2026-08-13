"""Add refund request metadata and reconciliation issues."""
from alembic import context, op
import sqlalchemy as sa

revision = "20260804_0033"
down_revision = "20260804_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if context.get_context().dialect.name == "sqlite":
        with op.batch_alter_table("refund_records", recreate="always") as batch:
            batch.add_column(sa.Column("requested_by_id", sa.Uuid(), nullable=True))
            batch.add_column(sa.Column("idempotency_key", sa.String(length=128), nullable=True))
            batch.create_foreign_key("fk_refund_records_requested_by", "auth_accounts", ["requested_by_id"], ["id"])
            batch.create_unique_constraint("uq_refund_records_idempotency_key", ["idempotency_key"])
    else:
        op.add_column("refund_records", sa.Column("requested_by_id", sa.Uuid(), nullable=True))
        op.add_column("refund_records", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
        op.create_foreign_key("fk_refund_records_requested_by", "refund_records", "auth_accounts", ["requested_by_id"], ["id"])
        op.create_unique_constraint("uq_refund_records_idempotency_key", "refund_records", ["idempotency_key"])
    op.create_table(
        "reconciliation_issues",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("payment_attempt_id", sa.Uuid(), sa.ForeignKey("payment_attempts.id"), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_reference", sa.String(length=255), nullable=False),
        sa.Column("local_status", sa.String(length=32), nullable=True),
        sa.Column("provider_status", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="OPEN"),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("resolved_by_id", sa.Uuid(), sa.ForeignKey("auth_accounts.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_reconciliation_issues_tenant_status", "reconciliation_issues", ["tenant_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_reconciliation_issues_tenant_status", table_name="reconciliation_issues")
    op.drop_table("reconciliation_issues")
    if context.get_context().dialect.name == "sqlite":
        with op.batch_alter_table("refund_records", recreate="always") as batch:
            batch.drop_constraint("uq_refund_records_idempotency_key", type_="unique")
            batch.drop_constraint("fk_refund_records_requested_by", type_="foreignkey")
            batch.drop_column("idempotency_key")
            batch.drop_column("requested_by_id")
    else:
        op.drop_constraint("uq_refund_records_idempotency_key", "refund_records", type_="unique")
        op.drop_constraint("fk_refund_records_requested_by", "refund_records", type_="foreignkey")
        op.drop_column("refund_records", "idempotency_key")
        op.drop_column("refund_records", "requested_by_id")

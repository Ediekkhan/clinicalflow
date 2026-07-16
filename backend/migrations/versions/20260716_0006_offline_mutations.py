"""Ticket versions and idempotent offline mutation receipts.

Revision ID: 20260716_0006
Revises: 20260716_0005
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260716_0006"
down_revision: str | None = "20260716_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.create_table(
        "client_mutations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_client_mutations_tenant_key", "client_mutations", ["tenant_id", "idempotency_key"], unique=True)
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE client_mutations ENABLE ROW LEVEL SECURITY")
        op.execute(
            "CREATE POLICY tenant_isolation_policy ON client_mutations "
            "USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
            "WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
        )


def downgrade() -> None:
    op.drop_table("client_mutations")
    op.drop_column("tickets", "version")

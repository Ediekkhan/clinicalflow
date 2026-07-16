"""Tenant-scoped cross-sector operational records.

Revision ID: 20260716_0010
Revises: 20260716_0009
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260716_0010"
down_revision: str | None = "20260716_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "operational_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("entity", sa.String(32), nullable=False),
        sa.Column("resource", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_operational_records_tenant_resource", "operational_records", ["tenant_id", "entity", "resource"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE operational_records ENABLE ROW LEVEL SECURITY")
        op.execute("CREATE POLICY tenant_isolation_policy ON operational_records USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)")


def downgrade() -> None:
    op.drop_table("operational_records")

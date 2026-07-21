"""Persist public demo requests.

Revision ID: 20260716_0004
Revises: 20260716_0003
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260716_0004"
down_revision: str | None = "20260716_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "demo_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("organization_name", sa.String(255)),
        sa.Column("work_email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(32)),
        sa.Column("facility_type", sa.String(128)),
        sa.Column("source", sa.String(64), nullable=False, server_default="WEBSITE"),
        sa.Column("daily_capacity", sa.Integer()),
        sa.Column("minutes_saved", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_demo_requests_tenant_created", "demo_requests", ["tenant_id", "created_at"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE demo_requests ENABLE ROW LEVEL SECURITY")
        op.execute(
            "CREATE POLICY tenant_isolation_policy ON demo_requests "
            "USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
            "WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
        )


def downgrade() -> None:
    op.drop_table("demo_requests")

"""Repair indexes missing from pre-Alembic local databases.

Revision ID: 20260716_0003
Revises: 20260716_0002
"""
from collections.abc import Sequence

from alembic import op

revision: str = "20260716_0003"
down_revision: str | None = "20260716_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS ix_tickets_tenant_queue ON tickets (tenant_id, queue_status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tickets_tenant_phone ON tickets (tenant_id, customer_phone)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_tenant_timestamp ON audit_logs (tenant_id, timestamp)")


def downgrade() -> None:
    # These indexes belong to the initial schema and must survive a downgrade to 0002.
    pass

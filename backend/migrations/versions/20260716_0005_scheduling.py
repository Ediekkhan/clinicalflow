"""Persistent provider scheduling engine.

Revision ID: 20260716_0005
Revises: 20260716_0004
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260716_0005"
down_revision: str | None = "20260716_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "providers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("specialty", sa.String(128), nullable=False),
        sa.Column("room_label", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_providers_tenant_id", "providers", ["tenant_id"])
    op.create_table(
        "provider_slots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("provider_id", sa.Uuid(), sa.ForeignKey("providers.id"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("lock_reason", sa.String(255)),
        sa.Column("is_booked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_provider_slots_tenant_start", "provider_slots", ["tenant_id", "starts_at"])
    op.create_index("ix_provider_slots_provider_start", "provider_slots", ["provider_id", "starts_at"], unique=True)
    op.create_table(
        "appointments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("tickets.id"), nullable=False),
        sa.Column("slot_id", sa.Uuid(), sa.ForeignKey("provider_slots.id"), nullable=False),
        sa.Column("customer_phone", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="BOOKED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_appointments_tenant_status", "appointments", ["tenant_id", "status"])
    op.create_index("ix_appointments_ticket", "appointments", ["ticket_id"])
    if op.get_bind().dialect.name == "postgresql":
        for table in ("providers", "provider_slots", "appointments"):
            op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
            op.execute(
                f'CREATE POLICY tenant_isolation_policy ON "{table}" '
                "USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
                "WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
            )


def downgrade() -> None:
    op.drop_table("appointments")
    op.drop_table("provider_slots")
    op.drop_table("providers")

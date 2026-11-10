"""Add nearest-facility routing fields.

Revision ID: 20260716_0011
Revises: 20260716_0010
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260716_0011"
down_revision: str | None = "20260716_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _is_postgresql() -> bool:
    return op.get_context().dialect.name == "postgresql"


def upgrade() -> None:
    op.add_column("tenants", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("tenants", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("tenants", sa.Column("accepts_patients", sa.Boolean(), nullable=False, server_default=sa.true()))

    op.add_column("tickets", sa.Column("patient_latitude", sa.Float(), nullable=True))
    op.add_column("tickets", sa.Column("patient_longitude", sa.Float(), nullable=True))
    if op.get_context().dialect.name == "sqlite":
        op.add_column("tickets", sa.Column("routed_tenant_id", sa.Uuid(), nullable=True))
    else:
        op.add_column("tickets", sa.Column("routed_tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=True))
    op.add_column("tickets", sa.Column("route_distance_km", sa.Float(), nullable=True))
    op.create_index("ix_tickets_routed_tenant_id", "tickets", ["routed_tenant_id"])
    op.execute("UPDATE tickets SET routed_tenant_id = tenant_id WHERE routed_tenant_id IS NULL")

    if _is_postgresql():
        op.execute('DROP POLICY IF EXISTS tenant_isolation_policy ON "tickets"')
        op.execute(
            '''
            CREATE POLICY tenant_isolation_policy ON "tickets"
            USING (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
                OR routed_tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            )
            WITH CHECK (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
                OR routed_tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            )
            '''
        )


def downgrade() -> None:
    if _is_postgresql():
        op.execute('DROP POLICY IF EXISTS tenant_isolation_policy ON "tickets"')
        op.execute(
            '''
            CREATE POLICY tenant_isolation_policy ON "tickets"
            USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
            WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
            '''
        )

    op.drop_index("ix_tickets_routed_tenant_id", table_name="tickets")
    op.drop_column("tickets", "route_distance_km")
    op.drop_column("tickets", "routed_tenant_id")
    op.drop_column("tickets", "patient_longitude")
    op.drop_column("tickets", "patient_latitude")

    op.drop_column("tenants", "accepts_patients")
    op.drop_column("tenants", "longitude")
    op.drop_column("tenants", "latitude")



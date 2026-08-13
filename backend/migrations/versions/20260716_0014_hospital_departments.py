"""Add hospital departments and provider availability.

Revision ID: 20260716_0014
Revises: 20260716_0013
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260716_0014"
down_revision: str | None = "20260716_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "hospital_departments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("hospital_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("coordinator_membership_id", sa.Uuid(), sa.ForeignKey("staff_memberships.id"), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("hospital_id", "code", name="uq_hospital_department_code"),
    )
    op.create_index("ix_hospital_departments_hospital_status", "hospital_departments", ["hospital_id", "status"])

    op.create_table(
        "provider_availability",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("membership_id", sa.Uuid(), sa.ForeignKey("staff_memberships.id"), nullable=False),
        sa.Column("hospital_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("department_id", sa.String(128), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="AVAILABLE"),
        sa.Column("maximum_appointments", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("booked_appointments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_provider_availability_membership_start", "provider_availability", ["membership_id", "starts_at"])
    op.create_index("ix_provider_availability_hospital_department", "provider_availability", ["hospital_id", "department_id", "status"])

    op.add_column("staff_memberships", sa.Column("daily_capacity", sa.Integer(), nullable=False, server_default="12"))

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in ("hospital_departments", "provider_availability"):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"CREATE POLICY tenant_isolation_policy ON {table} USING (hospital_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) WITH CHECK (hospital_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)")


def downgrade() -> None:
    op.drop_column("staff_memberships", "daily_capacity")
    op.drop_index("ix_provider_availability_hospital_department", table_name="provider_availability")
    op.drop_index("ix_provider_availability_membership_start", table_name="provider_availability")
    op.drop_table("provider_availability")
    op.drop_index("ix_hospital_departments_hospital_status", table_name="hospital_departments")
    op.drop_table("hospital_departments")

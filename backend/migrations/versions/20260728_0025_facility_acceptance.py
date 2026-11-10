"""facility acceptance history

Revision ID: 20260728_0025
Revises: 20260728_0024
"""
from alembic import context, op
import sqlalchemy as sa
revision = "20260728_0025"
down_revision = "20260728_0024"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("facility_acceptances", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("tickets.id"), nullable=False), sa.Column("facility_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False), sa.Column("actor_account_id", sa.Uuid(), sa.ForeignKey("auth_accounts.id"), nullable=False), sa.Column("actor_membership_id", sa.Uuid(), sa.ForeignKey("staff_memberships.id")), sa.Column("decision", sa.String(32), nullable=False), sa.Column("previous_status", sa.String(32), nullable=False), sa.Column("next_status", sa.String(32), nullable=False), sa.Column("reason", sa.Text()), sa.Column("redirected_facility_id", sa.Uuid(), sa.ForeignKey("tenants.id")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_facility_acceptances_ticket_created", "facility_acceptances", ["ticket_id", "created_at"])
    op.create_index("ix_facility_acceptances_facility_status", "facility_acceptances", ["facility_id", "decision"])
    bind = op.get_bind()
    if context.is_offline_mode() or bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE facility_acceptances ENABLE ROW LEVEL SECURITY")

def downgrade():
    op.drop_index("ix_facility_acceptances_facility_status", table_name="facility_acceptances")
    op.drop_index("ix_facility_acceptances_ticket_created", table_name="facility_acceptances")
    op.drop_table("facility_acceptances")


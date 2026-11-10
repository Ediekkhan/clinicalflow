"""Add auditable capability-based routing decisions.

Revision ID: 20260728_0020
Revises: 20260728_0019
"""
from collections.abc import Sequence

from alembic import context, op
import sqlalchemy as sa

revision: str = "20260728_0020"
down_revision: str | None = "20260728_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "routing_decisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("tickets.id"), nullable=False),
        sa.Column("patient_owner_tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("selected_facility_id", sa.Uuid(), sa.ForeignKey("tenants.id")),
        sa.Column("required_service", sa.String(128)),
        sa.Column("required_specialty", sa.String(128)),
        sa.Column("urgency", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="SELECTED"),
        sa.Column("selection_reason", sa.Text()),
        sa.Column("patient_preference_facility_id", sa.Uuid(), sa.ForeignKey("tenants.id")),
        sa.Column("manual_override_reason", sa.Text()),
        sa.Column("overridden_by_account_id", sa.Uuid(), sa.ForeignKey("auth_accounts.id")),
        sa.Column("overridden_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("ticket_id", name="uq_routing_decision_ticket"),
    )
    op.create_index("ix_routing_decisions_destination_created", "routing_decisions", ["selected_facility_id", "created_at"])
    op.create_table(
        "routing_candidates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("routing_decision_id", sa.Uuid(), sa.ForeignKey("routing_decisions.id"), nullable=False),
        sa.Column("facility_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("rank", sa.Integer()),
        sa.Column("eligible", sa.Boolean(), nullable=False),
        sa.Column("distance_km", sa.Float()),
        sa.Column("suitability_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("has_required_capability", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("has_emergency_capability", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("has_staff_coverage", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("has_capacity", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reasons_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("routing_decision_id", "facility_id", name="uq_routing_candidate_facility"),
    )
    op.create_index("ix_routing_candidates_decision_rank", "routing_candidates", ["routing_decision_id", "rank"])
    for table in ("routing_decisions", "routing_candidates"):
        if context.is_offline_mode():
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        elif op.get_bind().dialect.name == "postgresql":
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_routing_candidates_decision_rank", table_name="routing_candidates")
    op.drop_table("routing_candidates")
    op.drop_index("ix_routing_decisions_destination_created", table_name="routing_decisions")
    op.drop_table("routing_decisions")

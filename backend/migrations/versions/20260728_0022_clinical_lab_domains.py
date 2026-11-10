"""Add referral, longitudinal clinical record, and laboratory workflow domains.

Revision ID: 20260728_0022
Revises: 20260728_0021
"""
from collections.abc import Sequence

from alembic import context, op

from app.models import Base

revision: str = "20260728_0022"
down_revision: str | None = "20260728_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "referrals",
    "transfer_requests",
    "encounters",
    "care_teams",
    "care_team_members",
    "clinical_notes",
    "condition_records",
    "allergy_records",
    "medication_history",
    "procedure_records",
    "clinical_observations",
    "care_plans",
    "clinical_tasks",
    "clinical_documents",
    "laboratory_orders",
    "ordered_tests",
    "specimens",
    "accessions",
    "specimen_collections",
    "specimen_custody_events",
    "laboratory_results",
    "diagnostic_reports",
    "quality_control_reviews",
    "result_corrections",
    "critical_result_acknowledgements",
)


def upgrade() -> None:
    bind = op.get_bind()
    for name in TABLES:
        Base.metadata.tables[name].create(bind=bind)
    if context.is_offline_mode() or bind.dialect.name == "postgresql":
        for name in TABLES:
            op.execute(f"ALTER TABLE {name} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(TABLES):
        Base.metadata.tables[name].drop(bind=bind)

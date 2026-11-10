"""Add pharmacy, payer, government, country policy, and offline domains.

Revision ID: 20260728_0023
Revises: 20260728_0022
"""
from collections.abc import Sequence

from alembic import context, op

from app.models import Base

revision: str = "20260728_0023"
down_revision: str | None = "20260728_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "medications", "prescriptions", "prescription_items", "pharmacy_orders",
    "inventory_items", "stock_movements", "dispense_events", "substitution_requests",
    "interaction_alerts", "controlled_medication_logs", "pharmacy_deliveries", "patient_counselling",
    "payer_organizations", "health_plans", "member_coverages", "benefits", "provider_contracts",
    "eligibility_requests", "eligibility_responses", "prior_authorizations", "insurance_claims",
    "claim_items", "claim_responses", "denial_reasons", "claim_appeals", "remittances",
    "payment_reconciliations", "government_authorities", "government_user_scopes",
    "mandatory_disease_reports", "surveillance_aggregates", "national_indicators", "outbreak_alerts",
    "data_disclosures", "support_access_requests", "support_access_approvals", "country_packs",
    "interoperability_mappings", "offline_clinical_mutations",
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

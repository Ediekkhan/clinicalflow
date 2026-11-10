"""Align billing foreign-key indexes with the ORM models."""
from alembic import op

revision = "20260810_0034"
down_revision = "20260804_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_billing_customers_organization_id", "billing_customers", ["organization_id"])
    op.create_index("ix_checkout_sessions_organization_id", "checkout_sessions", ["organization_id"])
    op.create_index("ix_invoices_organization_id", "invoices", ["organization_id"])
    op.create_index("ix_payment_attempts_checkout_session_id", "payment_attempts", ["checkout_session_id"])
    op.create_index("ix_refund_records_payment_attempt_id", "refund_records", ["payment_attempt_id"])
    op.create_index("ix_subscriptions_organization_id", "subscriptions", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_subscriptions_organization_id", table_name="subscriptions")
    op.drop_index("ix_refund_records_payment_attempt_id", table_name="refund_records")
    op.drop_index("ix_payment_attempts_checkout_session_id", table_name="payment_attempts")
    op.drop_index("ix_invoices_organization_id", table_name="invoices")
    op.drop_index("ix_checkout_sessions_organization_id", table_name="checkout_sessions")
    op.drop_index("ix_billing_customers_organization_id", table_name="billing_customers")

"""Persist enterprise contact-sales enquiries."""
from alembic import op
import sqlalchemy as sa

revision = "20260804_0031"
down_revision = "20260804_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("subscription_plans", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("code", sa.String(64), nullable=False), sa.Column("name", sa.String(128), nullable=False), sa.Column("billing_interval", sa.String(32), nullable=False), sa.Column("price_minor", sa.Integer(), nullable=False), sa.Column("currency", sa.String(3), nullable=False), sa.Column("country_code", sa.String(2), nullable=False), sa.Column("stripe_price_id", sa.String(255)), sa.Column("paystack_plan_code", sa.String(255)), sa.Column("features_json", sa.Text(), nullable=False, server_default="[]"), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("code", "country_code", name="uq_subscription_plan_country"))
    op.create_table("billing_customers", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("organization_id", sa.Uuid(), nullable=False), sa.Column("provider", sa.String(32), nullable=False), sa.Column("provider_customer_id", sa.String(255), nullable=False), sa.Column("billing_email", sa.String(255), nullable=False), sa.Column("country_code", sa.String(2), nullable=False), sa.Column("currency", sa.String(3), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["organization_id"], ["tenants.id"]), sa.UniqueConstraint("provider", "provider_customer_id", name="uq_billing_customer_provider_ref"))
    op.create_table("checkout_sessions", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("organization_id", sa.Uuid(), nullable=False), sa.Column("plan_id", sa.Uuid(), nullable=False), sa.Column("provider", sa.String(32), nullable=False), sa.Column("public_reference", sa.String(64), nullable=False), sa.Column("provider_reference", sa.String(255), nullable=False), sa.Column("amount_minor", sa.Integer(), nullable=False), sa.Column("currency", sa.String(3), nullable=False), sa.Column("idempotency_key", sa.String(128), nullable=False), sa.Column("status", sa.String(32), nullable=False, server_default="CREATED"), sa.Column("expires_at", sa.DateTime(timezone=True)), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["organization_id"], ["tenants.id"]), sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"]), sa.UniqueConstraint("public_reference"), sa.UniqueConstraint("provider", "provider_reference", name="uq_checkout_session_provider_ref"), sa.UniqueConstraint("idempotency_key", name="uq_checkout_session_idempotency"))
    op.create_table("subscriptions", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("organization_id", sa.Uuid(), nullable=False), sa.Column("plan_id", sa.Uuid(), nullable=False), sa.Column("provider", sa.String(32), nullable=False), sa.Column("provider_subscription_id", sa.String(255), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("current_period_start", sa.DateTime(timezone=True)), sa.Column("current_period_end", sa.DateTime(timezone=True)), sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("cancellation_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["organization_id"], ["tenants.id"]), sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"]), sa.UniqueConstraint("provider", "provider_subscription_id", name="uq_subscription_provider_ref"))
    op.create_table("payment_attempts", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("checkout_session_id", sa.Uuid(), nullable=False), sa.Column("provider_transaction_reference", sa.String(255), unique=True), sa.Column("amount_minor", sa.Integer(), nullable=False), sa.Column("currency", sa.String(3), nullable=False), sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"), sa.Column("failure_code", sa.String(128)), sa.Column("failure_message", sa.String(512)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["checkout_session_id"], ["checkout_sessions.id"]))
    op.create_table("invoices", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("organization_id", sa.Uuid(), nullable=False), sa.Column("subscription_id", sa.Uuid()), sa.Column("provider", sa.String(32), nullable=False), sa.Column("provider_invoice_reference", sa.String(255), nullable=False), sa.Column("public_invoice_number", sa.String(64), nullable=False), sa.Column("amount_due_minor", sa.Integer(), nullable=False), sa.Column("amount_paid_minor", sa.Integer(), nullable=False, server_default="0"), sa.Column("currency", sa.String(3), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("due_at", sa.DateTime(timezone=True)), sa.Column("paid_at", sa.DateTime(timezone=True)), sa.Column("receipt_url", sa.String(1024)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["organization_id"], ["tenants.id"]), sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"]), sa.UniqueConstraint("provider", "provider_invoice_reference", name="uq_invoice_provider_ref"), sa.UniqueConstraint("public_invoice_number"))
    op.create_table("refund_records", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("payment_attempt_id", sa.Uuid(), nullable=False), sa.Column("provider_refund_reference", sa.String(255), unique=True), sa.Column("amount_minor", sa.Integer(), nullable=False), sa.Column("currency", sa.String(3), nullable=False), sa.Column("reason", sa.String(255)), sa.Column("status", sa.String(32), nullable=False, server_default="REQUESTED"), sa.Column("authorized_by_id", sa.Uuid()), sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False), sa.Column("processed_at", sa.DateTime(timezone=True)), sa.ForeignKeyConstraint(["payment_attempt_id"], ["payment_attempts.id"]), sa.ForeignKeyConstraint(["authorized_by_id"], ["auth_accounts.id"]))
    op.create_table(
        "payment_webhook_events",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_event_id", sa.String(length=255), nullable=False), sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False), sa.Column("processing_status", sa.String(length=32), nullable=False, server_default="RECEIVED"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True)), sa.Column("last_error", sa.Text()),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("provider", "provider_event_id", name="uq_payment_webhook_provider_event"),
    )
    op.create_table(
        "organization_onboarding_drafts",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("organization_type", sa.String(length=64)), sa.Column("current_step", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("country", sa.String(length=2)), sa.Column("draft_data_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("submitted_at", sa.DateTime(timezone=True)), sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["auth_accounts.id"]), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", name="uq_organization_onboarding_draft_account"),
    )
    op.create_table(
        "enterprise_enquiries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="NEW"),
        sa.Column("data_json", sa.Text(), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assigned_to_id", sa.Uuid(), nullable=True),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("follow_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["assigned_to_id"], ["auth_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference"),
    )
    op.create_index("ix_enterprise_enquiries_reference", "enterprise_enquiries", ["reference"], unique=True)
    op.create_index("ix_enterprise_enquiries_idempotency_key", "enterprise_enquiries", ["idempotency_key"], unique=True)
    op.create_index("ix_enterprise_enquiries_status_created", "enterprise_enquiries", ["status", "created_at"])


def downgrade() -> None:
    op.drop_table("refund_records")
    op.drop_table("invoices")
    op.drop_table("payment_attempts")
    op.drop_table("subscriptions")
    op.drop_table("checkout_sessions")
    op.drop_table("billing_customers")
    op.drop_table("subscription_plans")
    op.drop_table("payment_webhook_events")
    op.drop_index("ix_enterprise_enquiries_status_created", table_name="enterprise_enquiries")
    op.drop_index("ix_enterprise_enquiries_idempotency_key", table_name="enterprise_enquiries")
    op.drop_index("ix_enterprise_enquiries_reference", table_name="enterprise_enquiries")
    op.drop_table("enterprise_enquiries")
    op.drop_table("organization_onboarding_drafts")

"""Initial multi-tenant transactional schema and PostgreSQL RLS.

Revision ID: 20260716_0001
Revises: None
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260716_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_TABLES = ("staff", "auth_accounts", "auth_sessions", "tickets", "audit_logs")


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("state_location", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "staff",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("hashed_pin", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "auth_accounts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("identifier", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("first_name", sa.String(128), nullable=False),
        sa.Column("last_name", sa.String(128), nullable=False),
        sa.Column("phone", sa.String(32)),
        sa.Column("email", sa.String(255)),
        sa.Column("specialty", sa.String(128)),
        sa.Column("card_number", sa.String(64)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_accounts_tenant_id", "auth_accounts", ["tenant_id"])
    op.create_index("ix_auth_accounts_role", "auth_accounts", ["role"])
    op.create_index("ix_auth_accounts_identifier", "auth_accounts", ["identifier"], unique=True)
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("account_id", sa.Uuid(), sa.ForeignKey("auth_accounts.id"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("access_token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("refresh_token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("access_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("refresh_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("account_id", "tenant_id", "access_token_hash", "refresh_token_hash"):
        op.create_index(f"ix_auth_sessions_{column}", "auth_sessions", [column], unique=column.endswith("token_hash"))
    op.create_table(
        "tickets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("ticket_number", sa.String(64), nullable=False, unique=True),
        sa.Column("customer_phone", sa.String(32), nullable=False),
        sa.Column("account_group_phone", sa.String(32)),
        sa.Column("channel", sa.String(32), nullable=False, server_default="WEB"),
        sa.Column("urgency_level", sa.String(32), nullable=False, server_default="ROUTINE"),
        sa.Column("matched_condition_id", sa.String(128)),
        sa.Column("assigned_specialty", sa.String(128)),
        sa.Column("queue_status", sa.String(32), nullable=False, server_default="QUEUED"),
        sa.Column("is_manually_escalated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("appointment_slot", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tickets_tenant_queue", "tickets", ["tenant_id", "queue_status"])
    op.create_index("ix_tickets_tenant_phone", "tickets", ["tenant_id", "customer_phone"])
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("staff_id", sa.Uuid(), sa.ForeignKey("staff.id")),
        sa.Column("actor_id", sa.Uuid()),
        sa.Column("actor_type", sa.String(64), nullable=False, server_default="SYSTEM"),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(128)),
        sa.Column("resource_id", sa.Uuid()),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("log_metadata", sa.Text()),
        sa.Column("user_agent", sa.String(255)),
    )
    op.create_index("ix_audit_logs_tenant_timestamp", "audit_logs", ["tenant_id", "timestamp"])

    if op.get_bind().dialect.name == "postgresql":
        for table in TENANT_TABLES:
            op.execute(sa.text(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY'))
            op.execute(sa.text(
                f'CREATE POLICY tenant_isolation_policy ON "{table}" '
                "USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
                "WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
            ))


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for table in reversed(TENANT_TABLES):
            op.execute(sa.text(f'DROP POLICY IF EXISTS tenant_isolation_policy ON "{table}"'))
    op.drop_table("audit_logs")
    op.drop_table("tickets")
    op.drop_table("auth_sessions")
    op.drop_table("auth_accounts")
    op.drop_table("staff")
    op.drop_table("tenants")

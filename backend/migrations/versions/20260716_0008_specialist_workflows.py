"""Specialist assignment, notes, and messages.

Revision ID: 20260716_0008
Revises: 20260716_0007
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260716_0008"
down_revision: str | None = "20260716_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if op.get_context().as_sql:
        ticket_columns: set[str] = set()
        ticket_indexes: set[str] = set()
    else:
        inspector = sa.inspect(bind)
        ticket_columns = {column["name"] for column in inspector.get_columns("tickets")}
        ticket_indexes = {index["name"] for index in inspector.get_indexes("tickets")}
    if "assigned_specialist_id" not in ticket_columns:
        op.add_column("tickets", sa.Column("assigned_specialist_id", sa.Uuid(), nullable=True))
    if "ix_tickets_assigned_specialist_id" not in ticket_indexes:
        op.create_index("ix_tickets_assigned_specialist_id", "tickets", ["assigned_specialist_id"])
    if bind.dialect.name == "postgresql":
        op.create_foreign_key("fk_tickets_assigned_specialist", "tickets", "auth_accounts", ["assigned_specialist_id"], ["id"])
    op.create_table(
        "consultation_notes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("tickets.id"), nullable=False),
        sa.Column("specialist_id", sa.Uuid(), sa.ForeignKey("auth_accounts.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_consultation_notes_tenant_ticket", "consultation_notes", ["tenant_id", "ticket_id"])
    op.create_table(
        "specialist_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("specialist_id", sa.Uuid(), sa.ForeignKey("auth_accounts.id"), nullable=False),
        sa.Column("sender_label", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_specialist_messages_tenant_specialist", "specialist_messages", ["tenant_id", "specialist_id"])
    if op.get_bind().dialect.name == "postgresql":
        for table in ("consultation_notes", "specialist_messages"):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"CREATE POLICY tenant_isolation_policy ON {table} USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)")


def downgrade() -> None:
    op.drop_table("specialist_messages")
    op.drop_table("consultation_notes")
    if op.get_bind().dialect.name == "postgresql":
        op.drop_constraint("fk_tickets_assigned_specialist", "tickets", type_="foreignkey")
    op.drop_index("ix_tickets_assigned_specialist_id", table_name="tickets")
    op.drop_column("tickets", "assigned_specialist_id")

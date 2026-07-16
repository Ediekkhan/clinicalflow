"""Repair the specialist assignment foreign key on SQLite.

Revision ID: 20260716_0009
Revises: 20260716_0008
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260716_0009"
down_revision: str | None = "20260716_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite" or op.get_context().as_sql:
        return
    foreign_keys = sa.inspect(bind).get_foreign_keys("tickets")
    if not any(key.get("constrained_columns") == ["assigned_specialist_id"] for key in foreign_keys):
        with op.batch_alter_table("tickets") as batch_op:
            batch_op.create_foreign_key("fk_tickets_assigned_specialist", "auth_accounts", ["assigned_specialist_id"], ["id"])


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite" and not op.get_context().as_sql:
        with op.batch_alter_table("tickets") as batch_op:
            batch_op.drop_constraint("fk_tickets_assigned_specialist", type_="foreignkey")

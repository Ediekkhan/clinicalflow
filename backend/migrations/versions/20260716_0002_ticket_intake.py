"""Persist ticket intake text and extracted symptoms.

Revision ID: 20260716_0002
Revises: 20260716_0001
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260716_0002"
down_revision: str | None = "20260716_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("raw_intake_text", sa.Text(), nullable=True))
    op.add_column("tickets", sa.Column("extracted_symptoms", sa.Text(), nullable=True))
    op.execute(sa.text("UPDATE tickets SET raw_intake_text = 'Legacy intake unavailable' WHERE raw_intake_text IS NULL"))
    with op.batch_alter_table("tickets") as batch_op:
        batch_op.alter_column("raw_intake_text", existing_type=sa.Text(), nullable=False)


def downgrade() -> None:
    op.drop_column("tickets", "extracted_symptoms")
    op.drop_column("tickets", "raw_intake_text")

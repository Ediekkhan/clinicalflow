"""Persistent patient profile and health-card fields.

Revision ID: 20260716_0007
Revises: 20260716_0006
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260716_0007"
down_revision: str | None = "20260716_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PROFILE_COLUMNS = (
    sa.Column("date_of_birth", sa.DateTime(timezone=True), nullable=True),
    sa.Column("gender", sa.String(32), nullable=True),
    sa.Column("state", sa.String(128), nullable=True),
    sa.Column("lga", sa.String(128), nullable=True),
    sa.Column("emergency_contact", sa.String(32), nullable=True),
    sa.Column("hmo_provider", sa.String(128), nullable=True),
    sa.Column("blood_group", sa.String(8), nullable=True),
    sa.Column("genotype", sa.String(8), nullable=True),
    sa.Column("known_allergies", sa.Text(), nullable=True),
    sa.Column("current_medications", sa.Text(), nullable=True),
)


def upgrade() -> None:
    for column in PROFILE_COLUMNS:
        op.add_column("auth_accounts", column)


def downgrade() -> None:
    for column in reversed(PROFILE_COLUMNS):
        op.drop_column("auth_accounts", column.name)

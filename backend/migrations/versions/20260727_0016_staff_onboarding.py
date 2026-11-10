"""Add invitation-scoped staff onboarding fields.

Revision ID: 20260727_0016
Revises: 20260727_0015
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260727_0016"
down_revision: str | None = "20260727_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("staff_invitations", sa.Column("specialty_id", sa.String(128), nullable=True))
    op.add_column("staff_invitations", sa.Column("employment_type", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("staff_invitations", "employment_type")
    op.drop_column("staff_invitations", "specialty_id")
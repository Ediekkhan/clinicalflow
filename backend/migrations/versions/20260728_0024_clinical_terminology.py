"""Add versioned clinical terminology.

Revision ID: 20260728_0024
Revises: 20260728_0023
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

from app.models import Base

revision: str = "20260728_0024"
down_revision: str | None = "20260728_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "terminology_releases",
    "clinical_concepts",
    "concept_designations",
    "clinical_relationships",
    "clinical_content_reviews",
)


def upgrade() -> None:
    bind = op.get_bind()
    for name in TABLES:
        Base.metadata.tables[name].create(bind=bind)
    with op.batch_alter_table("tickets") as batch:
        batch.add_column(sa.Column("terminology_release_id", sa.Uuid(), nullable=True))
        batch.create_index("ix_tickets_terminology_release_id", ["terminology_release_id"])
        batch.create_foreign_key("fk_tickets_terminology_release", "terminology_releases", ["terminology_release_id"], ["id"])
    if context.is_offline_mode() or bind.dialect.name == "postgresql":
        for name in TABLES:
            op.execute(f"ALTER TABLE {name} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    with op.batch_alter_table("tickets") as batch:
        batch.drop_constraint("fk_tickets_terminology_release", type_="foreignkey")
        batch.drop_index("ix_tickets_terminology_release_id")
        batch.drop_column("terminology_release_id")
    bind = op.get_bind()
    for name in reversed(TABLES):
        Base.metadata.tables[name].drop(bind=bind)

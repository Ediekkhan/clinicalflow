"""Add verification document checksum and replacement metadata."""
from alembic import op
import sqlalchemy as sa

revision = "20260804_0032"
down_revision = "20260804_0031"
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table("verification_documents") as batch:
        batch.add_column(sa.Column("checksum_sha256", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("replaced_by_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key("fk_verification_documents_replaced_by", "verification_documents", ["replaced_by_id"], ["id"])

def downgrade() -> None:
    with op.batch_alter_table("verification_documents") as batch:
        batch.drop_constraint("fk_verification_documents_replaced_by", type_="foreignkey")
        batch.drop_column("replaced_by_id")
        batch.drop_column("checksum_sha256")

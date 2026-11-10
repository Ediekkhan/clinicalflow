"""Link application accounts to optional Supabase Auth identities."""
from alembic import op
import sqlalchemy as sa

revision = "20260731_0027"
down_revision = "20260728_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("auth_accounts") as batch:
        batch.add_column(sa.Column("supabase_user_id", sa.Uuid(), nullable=True))
        batch.create_index("ix_auth_accounts_supabase_user_id", ["supabase_user_id"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("auth_accounts") as batch:
        batch.drop_index("ix_auth_accounts_supabase_user_id")
        batch.drop_column("supabase_user_id")

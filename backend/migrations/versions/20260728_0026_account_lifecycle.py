"""Add account and session lifecycle fields.

Revision ID: 20260728_0026
Revises: 20260728_0025
"""
from alembic import op
import sqlalchemy as sa

revision = "20260728_0026"
down_revision = "20260728_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("auth_accounts") as batch:
        batch.add_column(sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    with op.batch_alter_table("auth_sessions") as batch:
        batch.add_column(sa.Column("revoked_reason", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("ip_address", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("user_agent", sa.String(length=512), nullable=True))
        batch.add_column(sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("auth_sessions") as batch:
        batch.drop_column("last_seen_at")
        batch.drop_column("user_agent")
        batch.drop_column("ip_address")
        batch.drop_column("revoked_reason")
    with op.batch_alter_table("auth_accounts") as batch:
        batch.drop_column("locked_until")
        batch.drop_column("failed_login_attempts")
        batch.drop_column("password_changed_at")
        batch.drop_column("email_verified_at")
        batch.drop_column("phone_verified_at")

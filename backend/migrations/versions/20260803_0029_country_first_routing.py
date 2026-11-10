"""country-first routing policy fields"""
from alembic import op
import sqlalchemy as sa

revision = "20260803_0029"
down_revision = "20260803_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("auth_accounts") as batch:
        batch.add_column(sa.Column("country_code", sa.String(2), nullable=False, server_default="NG"))
    with op.batch_alter_table("routing_decisions") as batch:
        batch.add_column(sa.Column("patient_country_code", sa.String(2)))
        batch.add_column(sa.Column("selected_hospital_country_code", sa.String(2)))
        batch.add_column(sa.Column("cross_border", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("eligibility_reasons", sa.Text()))
        batch.add_column(sa.Column("rejected_candidates", sa.Text()))
        batch.add_column(sa.Column("route_distance_km", sa.Float()))
        batch.add_column(sa.Column("routing_policy_version", sa.String(32), nullable=False, server_default="country-first-v1"))


def downgrade() -> None:
    with op.batch_alter_table("auth_accounts") as batch:
        batch.drop_column("country_code")
    with op.batch_alter_table("routing_decisions") as batch:
        for column in ("routing_policy_version", "route_distance_km", "rejected_candidates", "eligibility_reasons", "cross_border", "selected_hospital_country_code", "patient_country_code"):
            batch.drop_column(column)

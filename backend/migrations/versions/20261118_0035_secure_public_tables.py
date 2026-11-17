"""Secure public tables from direct Supabase Data API access.

Revision ID: 20261118_0035
Revises: 20260810_0034

ClinicalFlow reads and writes these tables through FastAPI using a direct
PostgreSQL connection. Browser clients do not need table-level access through
the Supabase Data API, so RLS is enabled with no anon/authenticated policies and
their existing privileges are revoked.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261118_0035"
down_revision: str | None = "20260810_0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PROTECTED_TABLES = (
    "alembic_version",
    "tenants",
    "hospital_doctor_memberships",
    "notifications",
    "facility_verification_cases",
    "external_registry_checks",
    "verification_findings",
    "facility_admin_activations",
    "billing_customers",
    "checkout_sessions",
    "subscription_plans",
    "subscriptions",
    "payment_attempts",
    "invoices",
    "payment_webhook_events",
    "organization_onboarding_drafts",
    "enterprise_enquiries",
    "refund_records",
    "reconciliation_issues",
)


def _quoted_table_list() -> str:
    return ", ".join(f'public."{table}"' for table in PROTECTED_TABLES)


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    for table in PROTECTED_TABLES:
        op.execute(
            sa.text(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')
        )

    # Supabase projects have these roles. The role guards keep the migration
    # compatible with ordinary PostgreSQL installations used by developers.
    tables = _quoted_table_list()
    op.execute(
        sa.text(
            f"""
            DO $secure_public_tables$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE {tables} FROM anon';
                END IF;
                IF EXISTS (
                    SELECT 1 FROM pg_roles WHERE rolname = 'authenticated'
                ) THEN
                    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE {tables} FROM authenticated';
                END IF;
            END
            $secure_public_tables$;
            """
        )
    )

    # Tables, sequences, and functions created by this migration role should
    # remain private unless a later migration explicitly opts them into an API.
    op.execute(
        sa.text(
            """
            DO $secure_default_privileges$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public
                        REVOKE ALL PRIVILEGES ON TABLES FROM anon;
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public
                        REVOKE ALL PRIVILEGES ON SEQUENCES FROM anon;
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public
                        REVOKE EXECUTE ON FUNCTIONS FROM anon;
                END IF;
                IF EXISTS (
                    SELECT 1 FROM pg_roles WHERE rolname = 'authenticated'
                ) THEN
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public
                        REVOKE ALL PRIVILEGES ON TABLES FROM authenticated;
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public
                        REVOKE ALL PRIVILEGES ON SEQUENCES FROM authenticated;
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public
                        REVOKE EXECUTE ON FUNCTIONS FROM authenticated;
                END IF;
            END
            $secure_default_privileges$;
            """
        )
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    for table in reversed(PROTECTED_TABLES):
        op.execute(
            sa.text(f'ALTER TABLE public."{table}" DISABLE ROW LEVEL SECURITY')
        )

    # Deliberately do not restore anon/authenticated grants. A schema downgrade
    # must not silently make patient, verification, or billing data public.

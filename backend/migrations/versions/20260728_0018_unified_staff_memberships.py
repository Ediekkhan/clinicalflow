"""Unify staff memberships with normalized departments and privileges.

Revision ID: 20260728_0018
Revises: 20260727_0017
"""
from collections.abc import Sequence
from datetime import UTC, datetime
import re
import uuid

from alembic import context, op
import sqlalchemy as sa

revision: str = "20260728_0018"
down_revision: str | None = "20260727_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _code(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "general"


def upgrade() -> None:
    op.create_table(
        "specialties",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("code", name="uq_specialties_code"),
    )
    op.create_index("ix_specialties_status_name", "specialties", ["status", "name"])
    with op.batch_alter_table("staff_memberships") as batch:
        batch.add_column(sa.Column("department_ref_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("specialty_ref_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("legacy_doctor_membership_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key("fk_staff_membership_department_ref", "hospital_departments", ["department_ref_id"], ["id"])
        batch.create_foreign_key("fk_staff_membership_specialty_ref", "specialties", ["specialty_ref_id"], ["id"])
        batch.create_foreign_key("fk_staff_membership_legacy_doctor", "hospital_doctor_memberships", ["legacy_doctor_membership_id"], ["id"])
        batch.create_unique_constraint("uq_staff_membership_legacy_doctor", ["legacy_doctor_membership_id"])
        batch.create_index("ix_staff_memberships_department_ref_id", ["department_ref_id"])
        batch.create_index("ix_staff_memberships_specialty_ref_id", ["specialty_ref_id"])
    op.create_table(
        "clinical_privileges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("membership_id", sa.Uuid(), sa.ForeignKey("staff_memberships.id"), nullable=False),
        sa.Column("code", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("granted_by_account_id", sa.Uuid(), sa.ForeignKey("auth_accounts.id")),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("membership_id", "code", name="uq_clinical_privilege_membership_code"),
    )
    op.create_index("ix_clinical_privileges_membership_status", "clinical_privileges", ["membership_id", "status"])

    if context.is_offline_mode():
        op.execute("ALTER TABLE specialties ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE clinical_privileges ENABLE ROW LEVEL SECURITY")
        return
    bind = op.get_bind()
    departments = list(bind.execute(sa.text("SELECT id, hospital_id, name, code FROM hospital_departments")).mappings())
    department_by_name = {(str(row["hospital_id"]), str(row["name"]).lower()): row["id"] for row in departments}
    department_by_code = {(str(row["hospital_id"]), str(row["code"]).lower()): row["id"] for row in departments}
    memberships = list(bind.execute(sa.text("SELECT id, user_id, hospital_id, department_id, specialty_id FROM staff_memberships")).mappings())
    specialty_names = sorted({str(row["specialty_id"]).strip() for row in memberships if row["specialty_id"]})
    legacy_rows = list(bind.execute(sa.text("SELECT * FROM hospital_doctor_memberships")).mappings())
    specialty_names.extend(str(row["specialty_id"]).strip() for row in legacy_rows if row["specialty_id"])
    specialty_ids: dict[str, uuid.UUID] = {}
    for name in sorted(set(specialty_names), key=str.lower):
        specialty_id = uuid.uuid4()
        specialty_ids[name.lower()] = specialty_id
        bind.execute(
            sa.text("INSERT INTO specialties (id, code, name, status, created_at) VALUES (:id, :code, :name, 'ACTIVE', :created_at)"),
            {"id": specialty_id, "code": _code(name), "name": name, "created_at": datetime.now(UTC)},
        )
    for row in memberships:
        hospital = str(row["hospital_id"])
        legacy_department = str(row["department_id"]).lower()
        department_ref = department_by_name.get((hospital, legacy_department)) or department_by_code.get((hospital, legacy_department))
        specialty_ref = specialty_ids.get(str(row["specialty_id"]).lower()) if row["specialty_id"] else None
        bind.execute(
            sa.text("UPDATE staff_memberships SET department_ref_id=:department_ref, specialty_ref_id=:specialty_ref WHERE id=:id"),
            {"department_ref": department_ref, "specialty_ref": specialty_ref, "id": row["id"]},
        )

    existing_keys = {
        (str(row["hospital_id"]), str(row["user_id"]), str(row["specialty_id"] or "").lower()): row["id"]
        for row in memberships
    }
    departments_by_hospital: dict[str, list[dict]] = {}
    for row in departments:
        departments_by_hospital.setdefault(str(row["hospital_id"]), []).append(row)
    for legacy in legacy_rows:
        key = (str(legacy["hospital_id"]), str(legacy["doctor_id"]), str(legacy["specialty_id"]).lower())
        if key in existing_keys:
            bind.execute(
                sa.text("UPDATE staff_memberships SET legacy_doctor_membership_id=:legacy_id WHERE id=:membership_id"),
                {"legacy_id": legacy["id"], "membership_id": existing_keys[key]},
            )
            continue
        candidates = sorted(departments_by_hospital.get(str(legacy["hospital_id"]), []), key=lambda item: (str(item["name"]), str(item["id"])))
        if not candidates:
            continue
        department = candidates[0]
        bind.execute(
            sa.text(
                "INSERT INTO staff_memberships "
                "(id, user_id, hospital_id, department_id, department_ref_id, role, specialty_id, specialty_ref_id, "
                "legacy_doctor_membership_id, verification_status, employment_status, notification_preferences, "
                "is_active, is_on_duty, daily_capacity, active_from, created_at, updated_at) "
                "VALUES (:id, :user_id, :hospital_id, :department_id, :department_ref_id, 'doctor', :specialty_id, "
                ":specialty_ref_id, :legacy_id, :verification_status, :employment_status, :notification_preferences, "
                ":is_active, 0, 12, :active_from, :created_at, :updated_at)"
            ),
            {
                "id": uuid.uuid4(),
                "user_id": legacy["doctor_id"],
                "hospital_id": legacy["hospital_id"],
                "department_id": department["name"],
                "department_ref_id": department["id"],
                "specialty_id": legacy["specialty_id"],
                "specialty_ref_id": specialty_ids.get(str(legacy["specialty_id"]).lower()),
                "legacy_id": legacy["id"],
                "verification_status": legacy["verification_status"],
                "employment_status": legacy["employment_status"],
                "notification_preferences": legacy["notification_preferences"],
                "is_active": legacy["is_active"],
                "active_from": legacy["active_from"],
                "created_at": legacy["active_from"],
                "updated_at": datetime.now(UTC),
            },
        )
    if bind.dialect.name == "postgresql":
        for table in ("specialties", "clinical_privileges"):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_clinical_privileges_membership_status", table_name="clinical_privileges")
    op.drop_table("clinical_privileges")
    with op.batch_alter_table("staff_memberships") as batch:
        batch.drop_index("ix_staff_memberships_specialty_ref_id")
        batch.drop_index("ix_staff_memberships_department_ref_id")
        batch.drop_constraint("uq_staff_membership_legacy_doctor", type_="unique")
        batch.drop_constraint("fk_staff_membership_legacy_doctor", type_="foreignkey")
        batch.drop_constraint("fk_staff_membership_specialty_ref", type_="foreignkey")
        batch.drop_constraint("fk_staff_membership_department_ref", type_="foreignkey")
        batch.drop_column("legacy_doctor_membership_id")
        batch.drop_column("specialty_ref_id")
        batch.drop_column("department_ref_id")
    op.drop_index("ix_specialties_status_name", table_name="specialties")
    op.drop_table("specialties")

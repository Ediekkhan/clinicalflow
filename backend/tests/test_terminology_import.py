import json
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models import AuthAccount, ClinicalContentReview, TerminologyRelease
from app.services.terminology_import import (
    TerminologyImportError,
    checksum_bytes,
    import_payload,
    local_payload,
    publish_release,
    rollback_release,
    validate_payload,
    validate_release,
)


@pytest_asyncio.fixture
async def app_session():
    with TestClient(app):
        async with app.state.session_factory() as session:
            yield session


@pytest.mark.asyncio
async def test_local_import_is_idempotent_and_has_licence_and_search_terms(app_session):
    session = app_session
    payload = local_payload()
    checksum = checksum_bytes(json.dumps(payload, sort_keys=True).encode())
    first = await import_payload(session, payload=payload, version="seed-1", checksum=checksum)
    second = await import_payload(session, payload=payload, version="seed-1", checksum=checksum)
    assert first.created is True
    assert second.created is False
    assert first.release_id == second.release_id
    assert first.concepts == 10
    assert first.designations >= 10
    report = await validate_release(session, first.release_id)
    assert report["valid"] is True
    release = await session.get(TerminologyRelease, first.release_id)
    assert release.license_reference


@pytest.mark.asyncio
async def test_duplicate_codes_invalid_file_shape_and_version_checksum_are_rejected(app_session):
    session = app_session
    payload = local_payload()
    payload["concepts"].append(dict(payload["concepts"][0]))
    assert any("duplicate concept code" in error for error in validate_payload(payload))
    with pytest.raises(TerminologyImportError):
        await import_payload(session, payload=payload, version="bad", checksum="bad")

    valid = local_payload()
    checksum = checksum_bytes(json.dumps(valid, sort_keys=True).encode())
    await import_payload(session, payload=valid, version="seed-2", checksum=checksum)
    with pytest.raises(TerminologyImportError, match="different checksum"):
        await import_payload(session, payload=valid, version="seed-2", checksum="changed")


@pytest.mark.asyncio
async def test_publication_requires_separate_review_and_rollback_restores_prior_release(app_session):
    session = app_session
    payload = local_payload()
    first = await import_payload(
        session,
        payload=payload,
        version="rollback-1",
        checksum=checksum_bytes(b"rollback-1"),
    )
    second = await import_payload(
        session,
        payload=payload,
        version="rollback-2",
        checksum=checksum_bytes(b"rollback-2"),
    )
    tenant_id = (await session.execute(select(AuthAccount.tenant_id).limit(1))).scalar_one()
    reviewer = AuthAccount(
        tenant_id=tenant_id,
        role="clinical_reviewer",
        identifier=f"reviewer-{uuid4().hex}",
        password_hash="test",
        first_name="Clinical",
        last_name="Reviewer",
        is_active=True,
    )
    publisher = AuthAccount(
        tenant_id=tenant_id,
        role="clinical_publisher",
        identifier=f"publisher-{uuid4().hex}",
        password_hash="test",
        first_name="Clinical",
        last_name="Publisher",
        is_active=True,
    )
    session.add_all([reviewer, publisher])
    await session.flush()
    with pytest.raises(TerminologyImportError):
        await publish_release(session, first.release_id, publisher.id)

    for release_id in (first.release_id, second.release_id):
        release = await session.get(TerminologyRelease, release_id)
        release.status = "APPROVED"
        session.add(
            ClinicalContentReview(
                resource_type="TerminologyRelease",
                resource_id=release_id,
                reviewer_account_id=reviewer.id,
                reviewer_role=reviewer.role,
                reviewer_organization_id=tenant_id,
                decision="APPROVED",
            )
        )
    await session.commit()
    await publish_release(session, first.release_id, publisher.id)
    first_release = await session.get(TerminologyRelease, first.release_id)
    first_release.status = "RETIRED"
    await session.commit()
    await publish_release(session, second.release_id, publisher.id)
    await rollback_release(session, second.release_id, first.release_id)
    assert (await session.get(TerminologyRelease, second.release_id)).status == "RETIRED"
    assert (await session.get(TerminologyRelease, first.release_id)).status == "PUBLISHED"




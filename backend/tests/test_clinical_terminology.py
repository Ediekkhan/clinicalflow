import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models import AuthAccount
from app.services.auth_service import ACCESS_COOKIE, REFRESH_COOKIE, create_session, hash_password


async def content_role_session(role: str):
    async with app.state.session_factory() as session:
        account = AuthAccount(
            tenant_id=uuid4(),
            role=role,
            identifier=f"{role}-{uuid4().hex}",
            password_hash=hash_password("Password123!"),
            first_name="Clinical",
            last_name="Reviewer",
            is_active=True,
        )
        # Use the configured tenant so the foreign key remains valid.
        from app.config import settings
        from uuid import UUID

        account.tenant_id = UUID(settings.default_tenant_id)
        session.add(account)
        await session.flush()
        issued = await create_session(session, account)
        await session.commit()
        return issued


def use_session(client, issued):
    client.cookies.set(ACCESS_COOKIE, issued.access_token)
    client.cookies.set(REFRESH_COOKIE, issued.refresh_token)


def create_draft(client, suffix: str):
    response = client.post("/api/v1/terminology/releases", json={
        "code_system": f"SV-LOCAL-{suffix}",
        "version": "1.0",
        "license_reference": "SynaptiVerse local reviewed content",
        "checksum": uuid4().hex,
        "language": "en",
    })
    assert response.status_code == 201, response.text
    return response.json()


def test_versioned_search_language_country_relationships_and_immutability():
    with TestClient(app) as client:
        login = client.post("/api/v1/auth/staff/pin-login", json={"role": "admin", "pin": "1357"})
        assert login.status_code == 200
        release = create_draft(client, uuid4().hex[:6])
        symptom = client.post(f"/api/v1/terminology/releases/{release['id']}/concepts", json={"external_code": "SYM-001", "concept_type": "SYMPTOM", "preferred_name": "Chest discomfort"})
        specialty = client.post(f"/api/v1/terminology/releases/{release['id']}/concepts", json={"external_code": "SP-001", "concept_type": "SPECIALTY", "preferred_name": "Emergency medicine"})
        assert symptom.status_code == specialty.status_code == 201
        designation = client.post(f"/api/v1/terminology/concepts/{symptom.json()['id']}/designations", json={"term": "chest dey pain me", "language_code": "pcm", "country_code": "NG", "term_type": "LOCAL_EXPRESSION", "review_status": "APPROVED"})
        relationship = client.post(f"/api/v1/terminology/releases/{release['id']}/relationships", json={"source_concept_id": symptom.json()["id"], "target_concept_id": specialty.json()["id"], "relationship_type": "ROUTES_TO", "country_code": "NG", "source_reference": "Local pilot mapping", "review_status": "APPROVED"})
        assert designation.status_code == relationship.status_code == 201

        reviewer = asyncio.run(content_role_session("clinical_reviewer"))
        use_session(client, reviewer)
        review = client.post(f"/api/v1/terminology/releases/{release['id']}/reviews", json={"decision": "APPROVED", "comments": "Approved for engineering pilot only", "evidence_reference": "Internal review"})
        assert review.status_code == 201

        publisher = asyncio.run(content_role_session("clinical_publisher"))
        use_session(client, publisher)
        published = client.post(f"/api/v1/terminology/releases/{release['id']}/publish")
        assert published.status_code == 200 and published.json()["status"] == "PUBLISHED"

        search = client.get("/api/v1/public/terminology/symptoms?q=chest%20dey&language=pcm&country=NG")
        assert search.status_code == 200 and search.json()[0]["code"] == "SYM-001"
        assert "license_reference" not in search.text and "source_url" not in search.text
        relationships = client.get(f"/api/v1/public/terminology/concepts/{symptom.json()['id']}/relationships?country=NG")
        assert relationships.status_code == 200 and relationships.json()[0]["target"]["code"] == "SP-001"
        immutable = client.post(f"/api/v1/terminology/releases/{release['id']}/concepts", json={"external_code": "SYM-002", "concept_type": "SYMPTOM", "preferred_name": "New symptom"})
        assert immutable.status_code == 409
        historical = client.get(f"/api/v1/terminology/resolve?code_system={release['code_system']}&code=SYM-001&version=1.0")
        assert historical.status_code == 200 and historical.json()["historical"] is True


def test_duplicate_release_and_concept_codes_are_rejected():
    with TestClient(app) as client:
        assert client.post("/api/v1/auth/staff/pin-login", json={"role": "admin", "pin": "1357"}).status_code == 200
        suffix = uuid4().hex[:6]
        release = create_draft(client, suffix)
        duplicate_release = client.post("/api/v1/terminology/releases", json={"code_system": release["code_system"], "version": "1.0", "license_reference": "Local", "checksum": uuid4().hex, "language": "en"})
        assert duplicate_release.status_code == 409
        body = {"external_code": "DUP-001", "concept_type": "DISORDER", "preferred_name": "Test disorder"}
        assert client.post(f"/api/v1/terminology/releases/{release['id']}/concepts", json=body).status_code == 201
        assert client.post(f"/api/v1/terminology/releases/{release['id']}/concepts", json=body).status_code == 409


def test_public_only_sees_published_active_content():
    with TestClient(app) as client:
        assert client.post("/api/v1/auth/staff/pin-login", json={"role": "admin", "pin": "1357"}).status_code == 200
        release = create_draft(client, uuid4().hex[:6])
        concept = client.post(f"/api/v1/terminology/releases/{release['id']}/concepts", json={"external_code": "DRAFT-001", "concept_type": "SYMPTOM", "preferred_name": "Draft-only symptom"})
        assert concept.status_code == 201
        public = client.get("/api/v1/public/terminology/concepts?q=Draft-only")
        assert public.status_code == 200 and public.json() == []


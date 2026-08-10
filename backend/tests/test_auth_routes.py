import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app


def test_patient_login_returns_profile_and_session_like_response() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/patient/login",
            json={"phone": "+2348012345678", "password": "Password123!"},
        )

        assert response.status_code == 200
        assert "clinicalflow_access" in response.cookies
        assert "clinicalflow_refresh" in response.cookies
        profile = client.get("/api/v1/auth/patient/me")

    payload = response.json()
    assert payload["role"] == "patient"
    assert payload["phone"] == "+2348012345678"
    assert payload["tenant_id"] == "11111111-1111-1111-1111-111111111111"
    assert profile.status_code == 200


def test_specialist_login_returns_profile_and_session_like_response() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/specialist/login",
            json={"email": "dr.ada@example.com", "password": "Password123!"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "specialist"
    assert payload["email"] == "dr.ada@example.com"
    assert payload["tenant_id"] == "11111111-1111-1111-1111-111111111111"


def test_refresh_rotates_session_and_logout_revokes_it() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/patient/login",
            json={"phone": "+2348012345678", "password": "Password123!"},
        )
        old_refresh = login.cookies["clinicalflow_refresh"]
        refreshed = client.post("/api/v1/auth/refresh")
        new_refresh = refreshed.cookies["clinicalflow_refresh"]
        logged_out = client.post("/api/v1/auth/logout")
        profile = client.get("/api/v1/auth/patient/me")

    assert refreshed.status_code == 200
    assert old_refresh != new_refresh
    assert logged_out.status_code == 204
    assert profile.status_code == 401


def test_invalid_credentials_are_rejected() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/patient/login",
            json={"phone": "+2348012345678", "password": "wrong-password"},
        )
    assert response.status_code == 401


def test_nurse_pin_login_and_role_cookie() -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/staff/pin-login", json={"role": "nurse", "pin": "2468"})
    assert response.status_code == 200
    assert response.json()["role"] == "nurse"
    assert response.cookies["clinicalflow_role"] == "nurse"


def test_admin_pin_login_reaches_admin_role() -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/staff/pin-login", json={"role": "admin", "pin": "1357"})
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_hospital_doctor_email_login_returns_persisted_profile() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/doctor/login",
            json={"email": "doctor.bassey@example.com", "password": "Password123!"},
        )
        profile = client.get("/api/v1/hospital/me")
    assert response.status_code == 200
    assert profile.status_code == 200
    assert profile.json()["role"] == "doctor"


def test_hospital_admin_email_login_uses_persisted_credentials() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/hospital_admin/login",
            json={"email": "admin.grace@example.com", "password": "Password123!"},
        )
        profile = client.get("/api/v1/hospital/me")
    assert response.status_code == 200
    assert profile.status_code == 200
    assert profile.json()["role"] == "hospital_admin"


def test_patient_cannot_use_staff_scheduler_mutation() -> None:
    with TestClient(app) as client:
        client.post(
            "/api/v1/auth/patient/login",
            json={"phone": "+2348012345678", "password": "Password123!"},
        )
        response = client.patch(
            "/api/v1/appointments/slots/11111111-1111-1111-1111-111111111111/lock",
            json={"is_locked": True, "reason": "Emergency block"},
        )
    assert response.status_code == 403


def test_nurse_can_load_public_safe_waiting_room_feed() -> None:
    with TestClient(app) as client:
        client.post("/api/v1/auth/staff/pin-login", json={"role": "nurse", "pin": "2468"})
        response = client.get("/api/v1/hospital/waiting-room")
    assert response.status_code == 200
    assert {"now_serving", "up_next", "departments"} <= response.json().keys()


def test_failed_logins_temporarily_lock_an_account() -> None:
    from app.config import settings

    previous_limit = settings.auth_max_failed_attempts
    previous_duration = settings.auth_lockout_minutes
    settings.auth_max_failed_attempts = 2
    settings.auth_lockout_minutes = 1
    try:
        with TestClient(app) as client:
            for _ in range(2):
                response = client.post(
                    "/api/v1/auth/patient/login",
                    json={"phone": "+2348012345678", "password": "wrong-password"},
                )
                assert response.status_code == 401
            locked = client.post(
                "/api/v1/auth/patient/login",
                json={"phone": "+2348012345678", "password": "Password123!"},
            )
        assert locked.status_code == 423
    finally:
        settings.auth_max_failed_attempts = previous_limit
        settings.auth_lockout_minutes = previous_duration

        async def reset_account() -> None:
            from sqlalchemy import select
            from app.models import AuthAccount

            async with app.state.session_factory() as session:
                account = await session.scalar(select(AuthAccount).where(AuthAccount.identifier == "+2348012345678"))
                assert account is not None
                account.failed_login_attempts = 0
                account.locked_until = None
                await session.commit()

        import asyncio
        asyncio.run(reset_account())


def test_logout_all_revokes_active_sessions() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/patient/login",
            json={"phone": "+2348012345678", "password": "Password123!"},
        )
        assert login.status_code == 200
        response = client.post("/api/v1/auth/logout-all")
        profile = client.get("/api/v1/auth/patient/me")

    assert response.status_code == 204
    assert profile.status_code == 401

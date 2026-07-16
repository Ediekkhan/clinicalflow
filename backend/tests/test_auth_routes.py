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
        assert "synaptiverse_access" in response.cookies
        assert "synaptiverse_refresh" in response.cookies
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
        old_refresh = login.cookies["synaptiverse_refresh"]
        refreshed = client.post("/api/v1/auth/refresh")
        new_refresh = refreshed.cookies["synaptiverse_refresh"]
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
    assert response.cookies["synaptiverse_role"] == "nurse"


def test_admin_pin_login_reaches_admin_role() -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/staff/pin-login", json={"role": "admin", "pin": "1357"})
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_hospital_doctor_login_returns_persisted_profile() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/hospital/account-login",
            json={"hospital_code": "UYO-FAMILY", "role": "doctor", "password": "Password123!"},
        )
        profile = client.get("/api/v1/hospital/me")
    assert response.status_code == 200
    assert profile.status_code == 200
    assert profile.json()["role"] == "doctor"


def test_hospital_nurse_and_admin_logins_use_their_persisted_credentials() -> None:
    credentials = (("nurse", "2468"), ("hospital_admin", "Password123!"))
    for role, password in credentials:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/hospital/account-login",
                json={"hospital_code": "UYO-FAMILY", "role": role, "password": password},
            )
            profile = client.get("/api/v1/hospital/me")
        assert response.status_code == 200
        assert profile.status_code == 200
        assert profile.json()["role"] == role


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

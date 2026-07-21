from fastapi.testclient import TestClient

from app.main import app


def test_public_landing_content_endpoints_are_available() -> None:
    with TestClient(app) as client:
        stats = client.get("/api/v1/public/platform-stats")
        pricing = client.get("/api/v1/public/pricing")
        posts = client.get("/api/v1/public/blog-posts")
        testimonials = client.get("/api/v1/public/testimonials")

    assert stats.status_code == 200
    assert stats.json()["channels_connected"] == 3
    assert len(pricing.json()["plans"]) == 3
    assert len(posts.json()) >= 1
    assert len(testimonials.json()) >= 1


def test_demo_request_is_persisted() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/public/demo-requests",
            json={
                "organization_name": "Pitch Test Clinic",
                "work_email": "operations@example.ng",
                "source": "ROI_CALCULATOR",
                "daily_capacity": 120,
                "minutes_saved": 7,
            },
        )
    assert response.status_code == 201
    assert response.json()["id"]


def test_demo_request_rejects_invalid_email() -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/public/demo-requests", json={"work_email": "not-an-email"})
    assert response.status_code == 422

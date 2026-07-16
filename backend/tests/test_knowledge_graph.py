import asyncio

from fastapi.testclient import TestClient

from app.main import app
from app.services.knowledge_graph import TRIAGE_QUERY, KnowledgeGraphService, extract_symptom_ids, fallback_route


def test_symptom_extraction_recognizes_supported_aliases() -> None:
    assert extract_symptom_ids("My body hot and I have been coughing") == ["fever", "cough"]


def test_fallback_escalates_red_flags_deterministically() -> None:
    route = fallback_route(["dizziness", "chest_pain"])
    assert route.derived_urgency == "CRITICAL"
    assert route.target_specialty == "Emergency Medicine"
    assert route.condition_id == "emergency_red_flag"
    assert route.source == "FALLBACK"


def test_disabled_graph_uses_safe_fallback() -> None:
    graph = KnowledgeGraphService(enabled=False, uri="", user="", password="")
    route = asyncio.run(graph.route("I have a rash"))
    assert route.condition_id == "dermatological_complaint"
    assert route.target_specialty == "Dermatology"


def test_graph_query_is_parameterized_and_contains_no_patient_data() -> None:
    assert "$extracted_symptom_ids" in TRIAGE_QUERY
    assert "customer_phone" not in TRIAGE_QUERY
    assert "raw_intake_text" not in TRIAGE_QUERY


def test_patient_triage_persists_the_graph_decision() -> None:
    with TestClient(app) as client:
        login = client.post("/api/v1/auth/patient/login", json={"phone": "+2348012345678", "password": "Password123!"})
        response = client.post("/api/v1/patient/triage", json={"symptom_description": "I have chest pain and feel dizzy"})
        tickets = client.get("/api/v1/tickets")

    assert login.status_code == 200
    assert response.status_code == 200
    payload = response.json()
    assert payload["urgency"] == "CRITICAL"
    assert payload["specialty"] == "Emergency Medicine"
    persisted = next(ticket for ticket in tickets.json() if ticket["id"] == payload["ticket"]["id"])
    assert persisted["matched_condition_id"] == "emergency_red_flag"
    assert persisted["assigned_specialty"] == "Emergency Medicine"


def test_public_triage_preview_routes_without_creating_a_ticket() -> None:
    with TestClient(app) as client:
        before = client.get("/api/v1/public/platform-stats").json()["patients_routed"]
        response = client.post("/api/v1/public/triage-preview", json={"symptom_description": "Sudden chest pain and difficulty breathing"})
        after = client.get("/api/v1/public/platform-stats").json()["patients_routed"]

    assert response.status_code == 200
    payload = response.json()
    assert payload["urgency"] == "CRITICAL"
    assert payload["specialty"] == "Emergency Medicine"
    assert payload["recommended_timing"] == "Seek emergency care now"
    assert after == before

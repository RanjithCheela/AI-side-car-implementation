import pytest
from httpx import AsyncClient, ASGITransport
from main import app


SAMPLE_APPLICATION = {
    "applicant": {
        "customer_id": "CUST-TEST-001",
        "name": "Ravi Kumar",
        "email": "ravi.kumar@example.com",
        "phone": "+919876543210",
        "date_of_birth": "1988-04-15",
        "national_id": "ABCDE1234F",
        "address": "42 MG Road, Bangalore, Karnataka 560001",
    },
    "loan": {
        "amount": 250000,
        "purpose": "Home renovation",
        "tenure_months": 24,
        "monthly_income": 65000,
        "employment_type": "salaried",
        "employer_name": "Infosys Ltd",
        "free_text_reason": "I want to renovate my kitchen and bathroom before my daughter's wedding next year.",
    },
    "device": {
        "device_id": "DEV-ANDROID-XYZ123",
        "ip_address": "203.0.113.42",
        "user_agent": "Mozilla/5.0 (Android 13; Mobile) Chrome/119",
        "session_id": "SES-ABC-999",
        "form_fill_duration_seconds": 312.5,
        "field_corrections": 3,
        "suspicious_pauses": False,
    },
}

HIGH_RISK_APPLICATION = {
    "applicant": {
        "customer_id": "CUST-RISK-999",
        "name": "John Doe",
        "email": "john@temp-mail.org",
        "phone": "+910000000000",
        "date_of_birth": "1990-01-01",
        "national_id": "XXXXX9999X",
        "address": "123 Unknown Street",
    },
    "loan": {
        "amount": 2000000,
        "purpose": "Medical emergency",
        "tenure_months": 12,
        "monthly_income": 30000,
        "employment_type": "self_employed",
        "free_text_reason": "URGENT! I need money immediately for critical surgery. Please approve fast.",
    },
    "device": {
        "device_id": "DEV-NEW-UNKNOWN",
        "ip_address": "10.0.0.1",
        "user_agent": "python-requests/2.31",
        "session_id": "SES-999-BOT",
        "form_fill_duration_seconds": 8.2,
        "field_corrections": 0,
        "suspicious_pauses": True,
    },
}


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_loan_application_returns_valid_response(client):
    resp = await client.post("/loan/apply", json=SAMPLE_APPLICATION)
    assert resp.status_code == 200
    data = resp.json()
    assert "application_id" in data
    assert data["action"] in ("ALLOW", "BLOCK", "ESCALATE", "CHALLENGE")
    assert "risk_assessment" in data
    assert "policy_decision" in data
    assert isinstance(data["risk_assessment"]["risk_score"], (int, float))
    assert 0 <= data["risk_assessment"]["risk_score"] <= 100
    assert isinstance(data["next_steps"], list)
    assert len(data["next_steps"]) > 0


@pytest.mark.asyncio
async def test_high_risk_application_does_not_allow(client):
    resp = await client.post("/loan/apply", json=HIGH_RISK_APPLICATION)
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] != "ALLOW", "High-risk bot-like application should not be allowed"
    assert data["risk_assessment"]["risk_score"] > 40


@pytest.mark.asyncio
async def test_audit_trail_created(client):
    resp = await client.post("/loan/apply", json=SAMPLE_APPLICATION)
    assert resp.status_code == 200
    app_id = resp.json()["application_id"]

    audit_resp = await client.get(f"/audit/{app_id}")
    assert audit_resp.status_code == 200
    audit_data = audit_resp.json()
    assert audit_data["application_id"] == app_id
    event_types = [e["type"] for e in audit_data["events"]]
    assert "CONTEXT_ENRICHED" in event_types
    assert "RISK_ASSESSED" in event_types


@pytest.mark.asyncio
async def test_audit_trail_not_found(client):
    resp = await client.get("/audit/non-existent-app-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_analytics_endpoint(client):
    await client.post("/loan/apply", json=SAMPLE_APPLICATION)
    resp = await client.get("/analytics/recent?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "records" in data
    assert all(k in data["summary"] for k in ("ALLOW", "BLOCK", "ESCALATE", "CHALLENGE"))

import io
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
# Endpoints now enforce role-based access; run the original suite as an Admin.
_token = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"}).json()["token"]
client.headers.update({"Authorization": f"Bearer {_token}"})


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard():
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "risk" in data
    assert "beds" in data
    assert "icu" in data
    assert "doctors" in data
    assert "hindsight" in data


def test_alerts():
    response = client.get("/api/v1/alerts")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_resource_history():
    response = client.get("/api/v1/resources/history")
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_hindsight():
    response = client.post("/api/v1/hindsight/search", json={
        "department": "Emergency",
        "current": {}
    })
    assert response.status_code == 200
    assert "matches" in response.json()
    assert len(response.json()["matches"]) > 0


def test_forecast():
    response = client.get("/api/v1/forecast?metric=admissions&horizon=7")
    assert response.status_code == 200
    data = response.json()
    assert data["metric"] == "admissions"
    assert len(data["forecast"]) == 7


def test_cascade():
    response = client.post("/api/v1/cascadeflow/analyze", json={
        "driver": "admissions",
        "change_pct": 25,
        "department": "Emergency"
    })
    assert response.status_code == 200
    assert len(response.json()["nodes"]) > 0


def test_simulation():
    response = client.post("/api/v1/simulations", json={
        "admissions_change_pct": 20
    })
    assert response.status_code == 200
    data = response.json()
    assert "simulated" in data
    assert "risk_score" in data["simulated"]
    assert "risk_level" in data["simulated"]


def test_decisions_flow():
    # Record a decision
    payload = {
        "issue": "ICU saturation imminent",
        "recommendation": "Divert non-trauma cases to St. Jude",
        "administrator_action": "Approved temporary EMS divert",
        "outcome": "in_progress",
        "department": "Emergency",
        "recorded_by": "Dr. Sarah Chen"
    }
    post_res = client.post("/api/v1/decisions", json=payload)
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "recorded"

    # Get decisions
    get_res = client.get("/api/v1/decisions")
    assert get_res.status_code == 200
    decisions = get_res.json()
    assert any(d["issue"] == "ICU saturation imminent" for d in decisions)


def test_auth_login():
    res = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    assert res.status_code == 200
    assert "token" in res.json()
    assert res.json()["user"]["username"] == "admin"


def test_upload_profile_and_commit():
    csv_content = (
        "date,department,admissions,emergency_cases,bed_occupancy,icu_occupancy,doctor_workload,staff_workload\n"
        "2026-10-10,Emergency,77,16,0.85,0.81,10.6,8.4\n"
        "2026-10-11,Emergency,79,17,0.87,0.83,11.0,8.6\n"
    ).encode("utf-8")

    # Profile
    files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
    profile_res = client.post("/api/v1/uploads/profile", files=files)
    assert profile_res.status_code == 200
    assert profile_res.json()["report"]["valid_records_after_basic_cleaning"] == 2

    # Commit to DB
    files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
    commit_res = client.post("/api/v1/uploads/commit", files=files)
    assert commit_res.status_code == 200
    assert commit_res.json()["status"] == "success"
    assert commit_res.json()["saved_count"] == 2


def test_database_relational_entities():
    # Verify all Phase 12 database tables are queryable
    dept_res = client.get("/api/v1/departments")
    assert dept_res.status_code == 200
    assert len(dept_res.json()) >= 4

    pat_res = client.get("/api/v1/patients")
    assert pat_res.status_code == 200
    assert len(pat_res.json()) >= 3

    doc_res = client.get("/api/v1/doctors")
    assert doc_res.status_code == 200
    assert len(doc_res.json()) >= 4

    staff_res = client.get("/api/v1/staff")
    assert staff_res.status_code == 200
    assert len(staff_res.json()) >= 3

    beds_res = client.get("/api/v1/beds")
    assert beds_res.status_code == 200
    assert len(beds_res.json()) >= 5

    rec_res = client.get("/api/v1/recommendations")
    assert rec_res.status_code == 200
    assert len(rec_res.json()) >= 1

    outcomes_res = client.get("/api/v1/decision-outcomes")
    assert outcomes_res.status_code == 200
    assert len(outcomes_res.json()) >= 1


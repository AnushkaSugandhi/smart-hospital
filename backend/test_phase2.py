import io

from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.db.models import AlertState, ResourceSnapshot, UploadBatch
from app.main import app
from app.services.alert_service import hours_until, predictive_alerts

client = TestClient(app)
HEADER = "date,department,admissions,emergency_cases,bed_occupancy,icu_occupancy,doctor_workload,staff_workload"


def auth(username="admin", password=None):
    password = password or {"admin": "admin123", "analyst": "analyst123", "viewer": "viewer123"}[username]
    token = client.post("/api/v1/auth/login", json={"username": username, "password": password}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


ADMIN, ANALYST, VIEWER = auth("admin"), auth("analyst"), auth("viewer")


def csv_file(body: str, name="test.csv"):
    return {"file": (name, io.BytesIO(body.encode()), "text/csv")}


# ---- Auth / roles ------------------------------------------------------------
def test_requires_login():
    assert client.get("/api/v1/dashboard/summary").status_code == 401
    assert client.get("/api/v1/dashboard/summary", headers={"Authorization": "Bearer forged.token"}).status_code == 401


def test_wrong_password_rejected_and_audited():
    assert client.post("/api/v1/auth/login", json={"username": "admin", "password": "hospital123"}).status_code == 401
    log = client.get("/api/v1/audit?action=login_failed", headers=ADMIN).json()
    assert log["total"] >= 1


def test_me_returns_token_user():
    me = client.get("/api/v1/auth/me", headers=VIEWER).json()
    assert me["username"] == "viewer" and me["role"] == "Viewer"


def test_roles_enforced_on_backend():
    body = HEADER + "\n2020-01-01,RoleTest,1,1,0.5,0.5,5,5\n"
    assert client.get("/api/v1/dashboard/summary", headers=VIEWER).status_code == 200
    assert client.post("/api/v1/uploads/commit", files=csv_file(body), headers=VIEWER).status_code == 403
    assert client.post("/api/v1/decisions", json={"issue": "x", "recommendation": "y", "administrator_action": "z"},
                       headers=VIEWER).status_code == 403
    assert client.get("/api/v1/audit", headers=ANALYST).status_code == 403
    assert client.post("/api/v1/uploads/batches/1/rollback", headers=ANALYST).status_code == 403


def test_patient_names_masked_for_non_admin():
    names = [p["name"] for p in client.get("/api/v1/patients", headers=ANALYST).json()]
    assert all(n.endswith("***") for n in names)


# ---- Dashboard ---------------------------------------------------------------
def test_summary_has_timestamp_trends_and_resources():
    d = client.get("/api/v1/dashboard/summary", headers=VIEWER).json()
    assert d["generated_at"]
    for key in ["bed_occupancy", "icu_occupancy", "doctor_workload", "emergency_cases", "risk_score"]:
        assert set(d["trends"][key]) >= {"change_pct", "direction", "improving"}
    keys = {r["key"] for r in d["resources"]}
    assert keys == {"ventilators", "operation_theatres", "nurses", "oxygen", "blood"}
    assert d["risk"]["breakdown"]


def test_config_is_public():
    cfg = client.get("/api/v1/config").json()
    assert cfg["status_bands"] == {"green_below": 70.0, "red_above": 85.0}


def test_hours_until_interpolates():
    assert hours_until(0.90, [0.94, 0.98], 0.95) == 30.0
    assert hours_until(0.90, [0.91, 0.92], 0.95) is None


def test_predictive_alert_fires_on_rising_icu():
    rows = [{"icu_occupancy": 0.70 + i * 0.012, "bed_occupancy": 0.6} for i in range(20)]
    alerts = predictive_alerts(rows, "2026-10-23")
    icu = [a for a in alerts if a["code"] == "ICU-FORECAST"]
    assert icu and "likely full in" in icu[0]["reason"]
    assert icu[0]["hours_until_full"] <= 72


# ---- Alerts state ------------------------------------------------------------
def test_acknowledge_and_snooze_persist():
    alerts = client.get("/api/v1/alerts?include_all=true", headers=ANALYST).json()
    assert len(alerts) >= 2, "seed data should produce at least two alerts"
    first, second = alerts[0]["id"], alerts[1]["id"]
    with SessionLocal() as db:
        db.query(AlertState).filter(AlertState.item_id.in_([first, second])).delete()
        db.commit()

    assert client.post(f"/api/v1/alerts/{first}/acknowledge", json={}, headers=VIEWER).status_code == 403
    assert client.post(f"/api/v1/alerts/{first}/acknowledge", json={"note": "on it"}, headers=ANALYST).status_code == 200
    assert client.post(f"/api/v1/alerts/{second}/snooze", json={"minutes": 30}, headers=ANALYST).status_code == 200

    active = {a["id"] for a in client.get("/api/v1/alerts", headers=VIEWER).json()}
    assert first not in active and second not in active
    states = {a["id"]: a["state"] for a in client.get("/api/v1/alerts?include_all=true", headers=VIEWER).json()}
    assert states[first] == "acknowledged" and states[second] == "snoozed"


# ---- Recommendations ---------------------------------------------------------
def test_next_actions_and_decide_logs_decision():
    recs = client.get("/api/v1/recommendations/next", headers=VIEWER).json()
    assert len(recs) <= 3
    if not recs:
        return
    rec = recs[0]
    assert rec["why"] and rec["impact"] and rec["risk_after"] <= rec["risk_before"]
    res = client.post(f"/api/v1/recommendations/next/{rec['id']}/decide", json={"decision": "approve"}, headers=ANALYST)
    assert res.status_code == 200 and res.json()["status"] == "approved"
    assert any(d["id"] == res.json()["decision"]["id"] for d in client.get("/api/v1/decisions", headers=VIEWER).json())
    with SessionLocal() as db:  # keep the test repeatable
        db.query(AlertState).filter(AlertState.item_id == rec["id"]).delete()
        db.commit()


# ---- Upload guidance & privacy -----------------------------------------------
def test_schema_and_template():
    schema = client.get("/api/v1/uploads/schema", headers=VIEWER).json()
    assert "date" in schema["required"] and "oxygen_stock_hours" in schema["optional"]
    assert schema["max_size_mb"] == 5
    template = client.get("/api/v1/uploads/template", headers=VIEWER)
    assert template.status_code == 200 and template.text.startswith("date,department")


def test_profile_masks_personal_fields_and_reports_row_errors():
    body = (
        HEADER + ",patient_name,phone\n"
        "2020-02-01,Emergency,70,15,82,0.8,10,8,Ravi Kumar,+91 98765 43210\n"
        "not-a-date,Emergency,70,15,80,0.8,10,8,Anita Rao,9876500000\n"
        "2020-02-03,Emergency,abc,15,80,0.8,10,8,Sam,9876500001\n"
        "2020-02-04,Emergency,70,15,80,1.5,10,8,Lee,9876500002\n"
    )
    report = client.post("/api/v1/uploads/profile", files=csv_file(body), headers=ANALYST).json()["report"]
    assert set(report["privacy"]["dropped_columns"]) == {"patient_name", "phone"}
    preview = report["raw_preview"][0]
    assert "Ravi" not in preview["patient_name"] and "43210" not in preview["phone"]
    assert any("percentage" in c for c in report["conversions"])  # 82 -> 0.82
    errors = {(e["row"], e["column"]) for e in report["row_errors"]}
    assert (3, "date") in errors and (4, "admissions") in errors
    assert report["valid_records_after_basic_cleaning"] == 1
    assert "patient_name" not in report["cleaned_preview"][0]


def test_upload_rejects_wrong_format():
    files = {"file": ("data.txt", io.BytesIO(b"hello"), "text/plain")}
    assert "error" in client.post("/api/v1/uploads/profile", files=files, headers=ANALYST).json()


# ---- Batches & rollback ------------------------------------------------------
def _value(dept, day):
    rows = client.get(f"/api/v1/resources/history?department={dept}", headers=VIEWER).json()
    match = [r for r in rows if r["date"] == day]
    return match[0]["admissions"] if match else None


def test_commit_creates_batch_and_rollback_restores_previous():
    dept, day = "RollbackTest", "2020-03-01"
    with SessionLocal() as db:
        db.query(ResourceSnapshot).filter(ResourceSnapshot.department == dept).delete()
        db.commit()

    a = client.post("/api/v1/uploads/commit", headers=ANALYST,
                    files=csv_file(HEADER + f",phone\n{day},{dept},50,10,0.6,0.6,8,7,9876543210\n")).json()
    b = client.post("/api/v1/uploads/commit", headers=ANALYST,
                    files=csv_file(HEADER + f"\n{day},{dept},60,10,0.6,0.6,8,7\n")).json()
    assert a["status"] == b["status"] == "success"
    assert a["dropped_columns"] == ["phone"]
    assert _value(dept, day) == 60

    batches = {x["id"]: x for x in client.get("/api/v1/uploads/batches", headers=VIEWER).json()}
    assert batches[b["batch_id"]]["uploaded_by"] == "analyst" and batches[b["batch_id"]]["row_count"] == 1
    assert client.get(f"/api/v1/uploads/batches/{b['batch_id']}", headers=ANALYST).json()["rows"][0]["admissions"] == 60

    r = client.post(f"/api/v1/uploads/batches/{b['batch_id']}/rollback", headers=ADMIN)
    assert r.status_code == 200 and r.json()["restored_rows"] == 1
    assert _value(dept, day) == 50
    assert client.post(f"/api/v1/uploads/batches/{b['batch_id']}/rollback", headers=ADMIN).status_code == 409

    client.post(f"/api/v1/uploads/batches/{a['batch_id']}/rollback", headers=ADMIN)
    assert _value(dept, day) is None
    with SessionLocal() as db:
        assert db.query(UploadBatch).get(a["batch_id"]).status == "rolled_back"


def test_rollback_older_batch_keeps_newer_data():
    dept, day = "RollbackOrder", "2020-04-01"
    a = client.post("/api/v1/uploads/commit", headers=ANALYST,
                    files=csv_file(HEADER + f"\n{day},{dept},11,1,0.5,0.5,5,5\n")).json()
    b = client.post("/api/v1/uploads/commit", headers=ANALYST,
                    files=csv_file(HEADER + f"\n{day},{dept},22,1,0.5,0.5,5,5\n")).json()
    client.post(f"/api/v1/uploads/batches/{a['batch_id']}/rollback", headers=ADMIN)
    assert _value(dept, day) == 22  # newer upload untouched
    client.post(f"/api/v1/uploads/batches/{b['batch_id']}/rollback", headers=ADMIN)
    assert _value(dept, day) is None


def test_optional_resource_columns_accepted():
    dept = "ResourceTest"
    body = (HEADER + ",ventilators_total,ventilators_in_use,oxygen_stock_hours,blood_o_neg\n"
            f"2020-05-01,{dept},10,2,0.5,0.5,5,5,20,19,8,3\n")
    res = client.post("/api/v1/uploads/commit", files=csv_file(body), headers=ANALYST).json()
    assert res["status"] == "success"
    cards = {c["key"]: c for c in client.get(f"/api/v1/resources?department={dept}", headers=VIEWER).json()}
    assert cards["ventilators"]["status"] == "critical" and cards["ventilators"]["low_stock"]
    assert cards["oxygen"]["status"] == "critical"
    assert cards["blood"]["available"] is False  # only one group supplied
    client.post(f"/api/v1/uploads/batches/{res['batch_id']}/rollback", headers=ADMIN)


def test_in_use_cannot_exceed_total():
    body = HEADER + ",ot_total,ot_in_use\n2020-06-01,Emergency,10,2,0.5,0.5,5,5,4,6\n"
    report = client.post("/api/v1/uploads/profile", files=csv_file(body), headers=ANALYST).json()["report"]
    assert report["row_errors"][0]["column"] == "ot_in_use"


# ---- Audit -------------------------------------------------------------------
def test_audit_filter_and_csv_export():
    client.post("/api/v1/decisions", headers=ANALYST, json={
        "issue": "Audit test", "recommendation": "r", "administrator_action": "a"})
    items = client.get("/api/v1/audit?action=decision_create&username=analyst", headers=ADMIN).json()["items"]
    assert items and items[0]["action"] == "decision_create" and items[0]["role"] == "Analyst"
    export = client.get("/api/v1/audit/export?action=upload_commit", headers=ADMIN)
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/csv")
    assert export.text.splitlines()[0].startswith("id,timestamp,username")
    meta = client.get("/api/v1/audit/meta", headers=ADMIN).json()
    assert "login" in meta["actions"]

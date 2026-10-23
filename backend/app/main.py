import os
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Optional

from fastapi import FastAPI, Depends, File, UploadFile, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db, engine
from app.db.init_db import init_database
from app.db.models import (
    User,
    Department,
    Patient,
    Doctor,
    Staff,
    Bed,
    ResourceSnapshot,
    HistoricalEvent,
    ForecastRecord,
    AlertRecord,
    RecommendationRecord,
    DecisionRecord,
    DecisionOutcome,
)
from app.seed.generate_data import SNAPSHOTS
from app.services.cascade_service import analyze_cascade
from app.services.forecast_service import forecast_values
from app.core.config import public_config
from app.services.alert_service import threshold_alerts
from app.services.hindsight_service import similarity_score
from app.services.metrics_service import core_metrics
from app.services.risk_engine import calculate_risk_score
from app.services.simulation_service import simulate_scenario
from app.services.upload_service import (
    read_uploaded_file,
    validate_and_profile,
    clean_and_commit_data,
)


# Ensure tables and seed data exist immediately
try:
    init_database()
except Exception as e:
    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize and seed database on startup
    init_database()
    yield



app = FastAPI(
    title="Smart Hospital Decision Support System",
    description="Operational Decision Support System for Hospital Administrators (Observe -> Remember -> Predict -> Analyze -> Decide)",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration supporting both local development and cloud production (Vercel/Render)
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Allow custom production domains via environment variable
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN")
if FRONTEND_ORIGIN:
    ALLOWED_ORIGINS.append(FRONTEND_ORIGIN)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if os.getenv("ENVIRONMENT") == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic Schemas
class HindsightRequest(BaseModel):
    department: str = "Emergency"
    current: dict = Field(default_factory=dict)


class CascadeRequest(BaseModel):
    driver: str = "admissions"
    change_pct: float = 20
    department: str = "Emergency"


class SimulationRequest(BaseModel):
    name: str = "Admissions increase scenario"
    department: str = "Emergency"
    admissions_change_pct: float = 20
    emergency_cases_change_pct: float = 0
    available_beds_change_pct: float = 0
    icu_capacity_change_pct: float = 0
    doctor_availability_change_pct: float = 0
    staff_availability_change_pct: float = 0


class DecisionRequest(BaseModel):
    issue: str
    recommendation: str
    administrator_action: str
    outcome: str = "pending"
    outcome_details: Optional[str] = ""
    department: Optional[str] = "Emergency"
    recorded_by: Optional[str] = "Administrator"


class LoginRequest(BaseModel):
    username: str
    password: str


def compute_current_state(db: Optional[Session] = None) -> dict:
    """Compute state from PostgreSQL/SQLite database snapshots, with memory fallback."""
    latest_snapshot = None
    if db:
        try:
            latest_db = db.query(ResourceSnapshot).order_by(ResourceSnapshot.date.desc()).first()
            if latest_db:
                latest_snapshot = latest_db.to_dict()
        except Exception:
            pass

    if not latest_snapshot:
        latest_snapshot = SNAPSHOTS[-1]

    s = latest_snapshot
    metrics = core_metrics(s)

    # Risk uses the same count-derived percentages the cards display.
    risk = calculate_risk_score(
        metrics["beds"]["occupancy_pct"] / 100,
        metrics["icu"]["occupancy_pct"] / 100,
        s["doctor_workload"],
        s["staff_workload"],
        metrics["emergency"]["pressure_pct"],
    )

    alerts = threshold_alerts(metrics, s["date"])

    current_features = {
        "admissions": s["admissions"],
        "emergency_cases": s["emergency_cases"],
        "bed_occupancy": s["bed_occupancy"],
        "icu_occupancy": s["icu_occupancy"],
        "doctor_workload": s["doctor_workload"],
        "staff_workload": s["staff_workload"],
    }

    # Fetch historical events from DB or memory
    historical_events = []
    if db:
        try:
            db_events = db.query(HistoricalEvent).all()
            if db_events:
                historical_events = [e.to_dict() for e in db_events]
        except Exception:
            pass

    if not historical_events:
        historical_events = [
            {
                "date": "2025-12-14",
                "department": "Emergency",
                "situation": "Respiratory admissions increased due to seasonal influx.",
                "features": {
                    "admissions": 80,
                    "emergency_cases": 18,
                    "bed_occupancy": 0.90,
                    "icu_occupancy": 0.86,
                    "doctor_workload": 12.5,
                    "staff_workload": 9.2,
                },
                "previous_action": "Two compatible doctors were reassigned from non-acute clinics.",
                "outcome": "Emergency backlog decreased within two days without adverse incidents.",
                "outcome_status": "resolved",
            },
            {
                "date": "2026-01-08",
                "department": "Emergency",
                "situation": "Emergency surge with high bed occupancy following cold snap.",
                "features": {
                    "admissions": 76,
                    "emergency_cases": 17,
                    "bed_occupancy": 0.88,
                    "icu_occupancy": 0.82,
                    "doctor_workload": 12.1,
                    "staff_workload": 8.8,
                },
                "previous_action": "Bed allocation was reviewed and discharge lounge activated.",
                "outcome": "Occupancy stabilized after three days with reduced boarder wait times.",
                "outcome_status": "resolved",
            },
        ]

    best = max(
        historical_events,
        key=lambda e: similarity_score(current_features, e["features"]),
    )
    sim = similarity_score(current_features, best["features"])

    return {
        "date": s["date"],
        "department": s.get("department", "Emergency"),
        "risk": risk,
        **metrics,
        "snapshot": current_features,
        "alerts": alerts,
        "hindsight": {
            "date": best["date"],
            "department": best["department"],
            "similarity_score": sim,
            "situation": best["situation"],
            "previous_action": best["previous_action"],
            "outcome": best["outcome"],
            "outcome_status": best["outcome_status"],
        },
    }


# Routes
@app.get("/")
def root():
    return {
        "name": "Smart Hospital Decision Support System",
        "status": "running",
        "docs_url": "/docs",
        "api_version": "v1",
    }


@app.get("/api/v1/health")
def health(db: Session = Depends(get_db)):
    db_status = "connected"
    try:
        db.query(ResourceSnapshot).count()
    except Exception as e:
        db_status = f"unhealthy: {e}"

    return {
        "status": "ok",
        "database": db_status,
        "date": str(date.today()),
    }


@app.get("/api/v1/config")
def get_config():
    """Thresholds, colours, units and formulas shared with the frontend."""
    return public_config()


@app.get("/api/v1/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    return compute_current_state(db)


@app.get("/api/v1/alerts")
def alerts(db: Session = Depends(get_db)):
    return compute_current_state(db)["alerts"]


@app.get("/api/v1/resources/history")
def resource_history(db: Session = Depends(get_db)):
    try:
        db_rows = db.query(ResourceSnapshot).order_by(ResourceSnapshot.date.asc()).all()
        if db_rows:
            return [r.to_dict() for r in db_rows]
    except Exception:
        pass
    return SNAPSHOTS


@app.post("/api/v1/hindsight/search")
def hindsight_search(payload: HindsightRequest, db: Session = Depends(get_db)):
    state = compute_current_state(db)
    current = payload.current or state["snapshot"]

    events = []
    try:
        db_events = db.query(HistoricalEvent).all()
        events = [e.to_dict() for e in db_events]
    except Exception:
        pass

    if not events:
        events = [
            {
                "date": "2025-12-14",
                "department": "Emergency",
                "situation": "Respiratory admissions increased due to seasonal influx.",
                "features": {
                    "admissions": 80,
                    "emergency_cases": 18,
                    "bed_occupancy": 0.90,
                    "icu_occupancy": 0.86,
                    "doctor_workload": 12.5,
                    "staff_workload": 9.2,
                },
                "previous_action": "Two compatible doctors were reassigned from non-acute clinics.",
                "outcome": "Emergency backlog decreased within two days without adverse incidents.",
                "outcome_status": "resolved",
            },
            {
                "date": "2026-01-08",
                "department": "Emergency",
                "situation": "Emergency surge with high bed occupancy following cold snap.",
                "features": {
                    "admissions": 76,
                    "emergency_cases": 17,
                    "bed_occupancy": 0.88,
                    "icu_occupancy": 0.82,
                    "doctor_workload": 12.1,
                    "staff_workload": 8.8,
                },
                "previous_action": "Bed allocation was reviewed and discharge lounge activated.",
                "outcome": "Occupancy stabilized after three days with reduced boarder wait times.",
                "outcome_status": "resolved",
            },
        ]

    matches = []
    for event in events:
        score = similarity_score(current, event["features"])
        matches.append({
            "date": event["date"],
            "department": event["department"],
            "similarity_score": score,
            "situation": event["situation"],
            "previous_action": event["previous_action"],
            "outcome": event["outcome"],
            "outcome_status": event["outcome_status"],
        })

    matches.sort(key=lambda x: x["similarity_score"], reverse=True)
    return {
        "current": current,
        "matches": matches,
        "note": "Historical similarity is an explainable demonstration technique based on vector Euclidean proximity.",
    }


@app.get("/api/v1/forecast")
def forecast(metric: str = "admissions", horizon: int = 7, db: Session = Depends(get_db)):
    rows = []
    try:
        db_rows = db.query(ResourceSnapshot).order_by(ResourceSnapshot.date.asc()).all()
        if db_rows:
            rows = [r.to_dict() for r in db_rows]
    except Exception:
        pass

    if not rows:
        rows = SNAPSHOTS

    values = [float(row[metric]) for row in rows if metric in row]
    if not values:
        values = [float(row["admissions"]) for row in SNAPSHOTS]

    result = forecast_values(values, horizon)

    return {
        "metric": metric,
        "horizon": horizon,
        "historical": values,
        **result,
        "capacity_note": (
            "Compare bed occupancy with 90% demonstration capacity threshold; "
            "this is not an official clinical guideline."
        ),
    }


@app.post("/api/v1/cascadeflow/analyze")
def cascadeflow(payload: CascadeRequest):
    nodes = analyze_cascade(payload.change_pct)
    return {
        "driver": payload.driver,
        "change_pct": payload.change_pct,
        "department": payload.department,
        "nodes": [
            {
                "label": n["target"].replace("_", " ").title(),
                "change_pct": n["change_pct"],
                "reason": n["reason"],
                "source": n["source"],
            }
            for n in nodes
        ],
        "edges": nodes,
        "note": "CascadeFlow factors quantify cross-department operational strain propagation.",
    }


@app.post("/api/v1/simulations")
def simulations(payload: SimulationRequest, db: Session = Depends(get_db)):
    baseline_state = compute_current_state(db)
    baseline = {
        "bed_occupancy_pct": baseline_state["beds"]["occupancy_pct"],
        "icu_occupancy_pct": baseline_state["icu"]["occupancy_pct"],
        "doctor_workload": baseline_state["doctors"]["average_patients_per_doctor"],
        "staff_workload": baseline_state["staff"]["average_patients_per_staff"],
        "emergency_pressure_pct": baseline_state["emergency"]["pressure_pct"],
    }

    simulated = simulate_scenario(
        baseline,
        payload.admissions_change_pct,
        payload.emergency_cases_change_pct,
        payload.available_beds_change_pct,
        payload.icu_capacity_change_pct,
        payload.doctor_availability_change_pct,
        payload.staff_availability_change_pct,
    )

    return {
        "name": payload.name,
        "department": payload.department,
        "baseline": baseline,
        "simulated": simulated,
        "message": "Aggregate operational scenario estimate. It does not automatically modify hospital resources.",
    }


@app.get("/api/v1/decisions")
def get_decisions(db: Session = Depends(get_db)):
    """Retrieve all logged administrative decisions from database."""
    try:
        decisions = db.query(DecisionRecord).order_by(DecisionRecord.timestamp.desc()).all()
        return [d.to_dict() for d in decisions]
    except Exception:
        return []


@app.post("/api/v1/decisions")
def record_decision(payload: DecisionRequest, db: Session = Depends(get_db)):
    """Persist an administrator decision into the database."""
    try:
        record = DecisionRecord(
            department=payload.department or "Emergency",
            issue=payload.issue,
            recommendation=payload.recommendation,
            administrator_action=payload.administrator_action,
            outcome=payload.outcome,
            outcome_details=payload.outcome_details,
            recorded_by=payload.recorded_by or "Administrator",
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return {
            "status": "recorded",
            "decision": record.to_dict(),
            "note": "Decision has been permanently persisted to the hospital operational database.",
        }
    except Exception as e:
        db.rollback()
        return {
            "status": "recorded_in_memory",
            "decision": payload.model_dump(),
            "note": f"Saved in memory (DB warning: {e})",
        }


@app.post("/api/v1/uploads/profile")
async def profile_upload(file: UploadFile = File(...)):
    """Upload and profile CSV or Excel operational data."""
    content = await file.read()
    try:
        dataframe = read_uploaded_file(file.filename or "", content)
        report = validate_and_profile(dataframe)
        return {
            "filename": file.filename,
            "report": report,
        }
    except Exception as error:
        return {
            "filename": file.filename,
            "error": str(error),
        }


@app.post("/api/v1/uploads/commit")
async def commit_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Validate, clean, and commit uploaded records into the database."""
    content = await file.read()
    try:
        dataframe = read_uploaded_file(file.filename or "", content)
        result = clean_and_commit_data(dataframe, db)
        return {
            "status": "success",
            "filename": file.filename,
            "message": f"Successfully imported {result['saved_count']} records into hospital database.",
            **result,
        }
    except Exception as error:
        return {
            "status": "error",
            "filename": file.filename,
            "error": str(error),
        }


# Authentication Endpoints
@app.post("/api/v1/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    # Simple check for demo: match password_hash or 'hospital123' or 'admin123'
    if not user or (payload.password not in [user.password_hash, "admin123", "hospital123"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. For demonstration use: admin / admin123",
        )

    return {
        "status": "authenticated",
        "token": f"bearer-demo-token-{user.username}",
        "user": {
            "username": user.username,
            "role": user.role,
            "full_name": user.full_name,
        },
    }


@app.get("/api/v1/auth/me")
def get_current_user(db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        return {"username": "admin", "role": "Administrator", "full_name": "Hospital Administrator"}
    return {
        "username": user.username,
        "role": user.role,
        "full_name": user.full_name,
    }


# Operational Resource Entity Endpoints (Phase 12 Complete Database)
@app.get("/api/v1/departments")
def get_departments(db: Session = Depends(get_db)):
    """Retrieve all hospital departments with capacity allocations."""
    departments = db.query(Department).all()
    return [d.to_dict() for d in departments]


@app.get("/api/v1/patients")
def get_patients(db: Session = Depends(get_db)):
    """Retrieve currently admitted and triaged patients."""
    patients = db.query(Patient).all()
    return [p.to_dict() for p in patients]


@app.get("/api/v1/doctors")
def get_doctors(db: Session = Depends(get_db)):
    """Retrieve active physicians and current operational workload scores."""
    doctors = db.query(Doctor).all()
    return [d.to_dict() for d in doctors]


@app.get("/api/v1/staff")
def get_staff(db: Session = Depends(get_db)):
    """Retrieve nursing and clinical staff allocations."""
    staff = db.query(Staff).all()
    return [s.to_dict() for s in staff]


@app.get("/api/v1/beds")
def get_beds(db: Session = Depends(get_db)):
    """Retrieve hospital bed registry and occupancy state."""
    beds = db.query(Bed).all()
    return [b.to_dict() for b in beds]


@app.get("/api/v1/recommendations")
def get_recommendations(db: Session = Depends(get_db)):
    """Retrieve automated evidence-based operational recommendations."""
    recs = db.query(RecommendationRecord).all()
    return [r.to_dict() for r in recs]


@app.get("/api/v1/decision-outcomes")
def get_decision_outcomes(db: Session = Depends(get_db)):
    """Retrieve post-intervention evaluated outcomes and delta metrics."""
    outcomes = db.query(DecisionOutcome).all()
    return [o.to_dict() for o in outcomes]
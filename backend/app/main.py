import os
from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import auth as auth_routes
from app.api import data as data_routes
from app.api import ops as ops_routes
from app.core.config import public_config
from app.core.security import CurrentUser, analyst, viewer
from app.db.database import get_db
from app.db.init_db import init_database
from app.db.models import (
    Department,
    Patient,
    Doctor,
    Staff,
    Bed,
    ResourceSnapshot,
    RecommendationRecord,
    DecisionRecord,
    DecisionOutcome,
)
from app.services import audit_service, snapshot_service
from app.services.cascade_service import analyze_cascade
from app.services.forecast_service import forecast_values
from app.services.hindsight_service import similarity_score
from app.services.recommendation_service import baseline_from_state
from app.services.simulation_service import simulate_scenario
from app.services.state_service import compute_current_state, historical_events
from app.services.upload_service import mask_value


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
    version="2.0.0",
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
    ALLOWED_ORIGINS.extend(o.strip() for o in FRONTEND_ORIGIN.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if os.getenv("ENVIRONMENT") == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(data_routes.router)
app.include_router(ops_routes.router)


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
    recorded_by: Optional[str] = None


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
def dashboard_summary(department: Optional[str] = None, db: Session = Depends(get_db),
                      user: CurrentUser = Depends(viewer)):
    return compute_current_state(db, department)


@app.get("/api/v1/departments/active")
def active_departments(db: Session = Depends(get_db), user: CurrentUser = Depends(viewer)):
    """Departments that have snapshot data (for the department filter)."""
    return snapshot_service.departments(db)


@app.get("/api/v1/resources/history")
def resource_history(department: Optional[str] = None, db: Session = Depends(get_db),
                     user: CurrentUser = Depends(viewer)):
    return snapshot_service.series(db, department)


@app.post("/api/v1/hindsight/search")
def hindsight_search(payload: HindsightRequest, db: Session = Depends(get_db),
                     user: CurrentUser = Depends(viewer)):
    state = compute_current_state(db)
    current = payload.current or state["snapshot"]

    matches = []
    for event in historical_events(db):
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


def forecast_payload(db: Session, metric: str = "admissions", horizon: int = 7,
                     department: Optional[str] = None) -> dict:
    rows = snapshot_service.series(db, department)
    values = [float(row[metric]) for row in rows if row.get(metric) is not None]
    if not values:
        metric = "admissions"
        values = [float(row["admissions"]) for row in rows]
    horizon = max(1, min(int(horizon), 30))

    result = forecast_values(values, horizon)
    return {
        "metric": metric,
        "horizon": horizon,
        "historical": values,
        "dates": [row["date"] for row in rows if row.get(metric) is not None],
        **result,
        "capacity_note": (
            "Compare bed occupancy with 90% demonstration capacity threshold; "
            "this is not an official clinical guideline."
        ),
    }


@app.get("/api/v1/forecast")
def forecast(metric: str = "admissions", horizon: int = 7, department: Optional[str] = None,
             db: Session = Depends(get_db), user: CurrentUser = Depends(viewer)):
    return forecast_payload(db, metric, horizon, department)


@app.post("/api/v1/cascadeflow/analyze")
def cascadeflow(payload: CascadeRequest, user: CurrentUser = Depends(viewer)):
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


def run_simulation_payload(db: Session, payload: SimulationRequest) -> dict:
    baseline_state = compute_current_state(db)
    baseline = baseline_from_state(baseline_state)

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
        "baseline": {**baseline, "risk_score": baseline_state["risk"]["score"],
                     "risk_level": baseline_state["risk"]["level"]},
        "simulated": simulated,
        "message": "Aggregate operational scenario estimate. It does not automatically modify hospital resources.",
    }


@app.post("/api/v1/simulations")
def simulations(payload: SimulationRequest, db: Session = Depends(get_db),
                user: CurrentUser = Depends(viewer)):
    return run_simulation_payload(db, payload)


@app.get("/api/v1/decisions")
def get_decisions(db: Session = Depends(get_db), user: CurrentUser = Depends(viewer)):
    """Retrieve all logged administrative decisions from database."""
    try:
        decisions = db.query(DecisionRecord).order_by(DecisionRecord.timestamp.desc()).all()
        return [d.to_dict() for d in decisions]
    except Exception:
        return []


@app.post("/api/v1/decisions")
def record_decision(payload: DecisionRequest, db: Session = Depends(get_db),
                    user: CurrentUser = Depends(analyst)):
    """Persist an administrator decision into the database."""
    try:
        record = DecisionRecord(
            department=payload.department or "Emergency",
            issue=payload.issue,
            recommendation=payload.recommendation,
            administrator_action=payload.administrator_action,
            outcome=payload.outcome,
            outcome_details=payload.outcome_details,
            recorded_by=payload.recorded_by or f"{user.full_name or user.username} ({user.role})",
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        audit_service.record(db, user, "decision_create", "decision", record.id,
                             {"issue": payload.issue, "action": payload.administrator_action})
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


# Operational Resource Entity Endpoints (Phase 12 Complete Database)
@app.get("/api/v1/departments")
def get_departments(db: Session = Depends(get_db), user: CurrentUser = Depends(viewer)):
    """Retrieve all hospital departments with capacity allocations."""
    departments = db.query(Department).all()
    return [d.to_dict() for d in departments]


@app.get("/api/v1/patients")
def get_patients(db: Session = Depends(get_db), user: CurrentUser = Depends(analyst)):
    """Retrieve admitted patients. Names are masked for everyone except Admins."""
    patients = [p.to_dict() for p in db.query(Patient).all()]
    if not user.has_role("Admin"):
        for p in patients:
            p["name"] = mask_value(p["name"])
    return patients


@app.get("/api/v1/doctors")
def get_doctors(db: Session = Depends(get_db), user: CurrentUser = Depends(viewer)):
    """Retrieve active physicians and current operational workload scores."""
    doctors = db.query(Doctor).all()
    return [d.to_dict() for d in doctors]


@app.get("/api/v1/staff")
def get_staff(db: Session = Depends(get_db), user: CurrentUser = Depends(viewer)):
    """Retrieve nursing and clinical staff allocations."""
    staff = db.query(Staff).all()
    return [s.to_dict() for s in staff]


@app.get("/api/v1/beds")
def get_beds(db: Session = Depends(get_db), user: CurrentUser = Depends(viewer)):
    """Retrieve hospital bed registry and occupancy state."""
    beds = db.query(Bed).all()
    return [b.to_dict() for b in beds]


@app.get("/api/v1/recommendations")
def get_recommendations(db: Session = Depends(get_db), user: CurrentUser = Depends(viewer)):
    """Retrieve automated evidence-based operational recommendations."""
    recs = db.query(RecommendationRecord).all()
    return [r.to_dict() for r in recs]


@app.get("/api/v1/decision-outcomes")
def get_decision_outcomes(db: Session = Depends(get_db), user: CurrentUser = Depends(viewer)):
    """Retrieve post-intervention evaluated outcomes and delta metrics."""
    outcomes = db.query(DecisionOutcome).all()
    return [o.to_dict() for o in outcomes]

"""Read-only analytics shared by the API routes and the chatbot's tools."""
from typing import Optional

from sqlalchemy.orm import Session

from app.services import snapshot_service
from app.services.forecast_service import forecast_values
from app.services.recommendation_service import baseline_from_state
from app.services.simulation_service import simulate_scenario
from app.services.state_service import compute_current_state


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


def run_simulation_payload(db: Session, payload) -> dict:
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

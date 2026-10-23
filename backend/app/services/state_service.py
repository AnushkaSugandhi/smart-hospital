"""Current hospital state: the single computation behind the dashboard,
alerts, recommendations and the chatbot's numeric tools."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import HistoricalEvent
from app.services import snapshot_service
from app.services.alert_service import predictive_alerts, stock_alerts, threshold_alerts
from app.services.hindsight_service import similarity_score
from app.services.metrics_service import core_metrics
from app.services.resources_service import resource_cards
from app.services.risk_engine import calculate_risk_score
from app.services.trends import trend

FEATURE_KEYS = ["admissions", "emergency_cases", "bed_occupancy", "icu_occupancy", "doctor_workload", "staff_workload"]

FALLBACK_EVENTS = [
    {
        "date": "2025-12-14",
        "department": "Emergency",
        "situation": "Respiratory admissions increased due to seasonal influx.",
        "features": {"admissions": 80, "emergency_cases": 18, "bed_occupancy": 0.90,
                     "icu_occupancy": 0.86, "doctor_workload": 12.5, "staff_workload": 9.2},
        "previous_action": "Two compatible doctors were reassigned from non-acute clinics.",
        "outcome": "Emergency backlog decreased within two days without adverse incidents.",
        "outcome_status": "resolved",
    },
    {
        "date": "2026-01-08",
        "department": "Emergency",
        "situation": "Emergency surge with high bed occupancy following cold snap.",
        "features": {"admissions": 76, "emergency_cases": 17, "bed_occupancy": 0.88,
                     "icu_occupancy": 0.82, "doctor_workload": 12.1, "staff_workload": 8.8},
        "previous_action": "Bed allocation was reviewed and discharge lounge activated.",
        "outcome": "Occupancy stabilized after three days with reduced boarder wait times.",
        "outcome_status": "resolved",
    },
]


def historical_events(db: Optional[Session]) -> list[dict]:
    if db is not None:
        try:
            events = [e.to_dict() for e in db.query(HistoricalEvent).all()]
            if events:
                return events
        except Exception:
            pass
    return FALLBACK_EVENTS


def _risk(snapshot: dict, metrics: dict) -> dict:
    # Risk uses the same count-derived percentages the cards display.
    return calculate_risk_score(
        metrics["beds"]["occupancy_pct"] / 100,
        metrics["icu"]["occupancy_pct"] / 100,
        snapshot["doctor_workload"],
        snapshot["staff_workload"],
        metrics["emergency"]["pressure_pct"],
    )


def kpi_values(metrics: dict, risk: dict) -> dict:
    return {
        "bed_occupancy": metrics["beds"]["occupancy_pct"],
        "icu_occupancy": metrics["icu"]["occupancy_pct"],
        "doctor_workload": metrics["doctors"]["average_patients_per_doctor"],
        "staff_workload": metrics["staff"]["average_patients_per_staff"],
        "emergency_cases": metrics["emergency"]["active_cases"],
        "risk_score": risk["score"],
    }


def compute_current_state(db: Optional[Session] = None, department: Optional[str] = None) -> dict:
    rows = snapshot_service.series(db, department)
    s = rows[-1]
    prev = rows[-2] if len(rows) > 1 else None

    metrics = core_metrics(s)
    risk = _risk(s, metrics)

    current_kpis = kpi_values(metrics, risk)
    trends = {}
    if prev:
        prev_metrics = core_metrics(prev)
        prev_kpis = kpi_values(prev_metrics, _risk(prev, prev_metrics))
        trends = {k: trend(current_kpis[k], prev_kpis[k], higher_is_worse=True) for k in current_kpis}
    else:
        trends = {k: trend(current_kpis[k], None) for k in current_kpis}

    resources = resource_cards(rows)
    alerts = (
        threshold_alerts(metrics, s["date"])
        + predictive_alerts(rows, s["date"])
        + stock_alerts(resources, s["date"])
    )
    alerts.sort(key=lambda a: (a["severity"] != "critical", a.get("kind") != "predictive"))

    current_features = {k: s[k] for k in FEATURE_KEYS}
    events = historical_events(db)
    best = max(events, key=lambda e: similarity_score(current_features, e["features"]))

    data_ts = snapshot_service.latest_data_timestamp(db) if db is not None else None
    return {
        "date": s["date"],
        "department": s.get("department", "Emergency"),
        "departments": snapshot_service.departments(db) if db is not None else ["Emergency"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_updated_at": data_ts.replace(tzinfo=timezone.utc).isoformat() if data_ts else None,
        "risk": risk,
        **metrics,
        "snapshot": current_features,
        "trends": trends,
        "resources": resources,
        "alerts": alerts,
        "hindsight": {
            "date": best["date"],
            "department": best["department"],
            "similarity_score": similarity_score(current_features, best["features"]),
            "situation": best["situation"],
            "previous_action": best["previous_action"],
            "outcome": best["outcome"],
            "outcome_status": best["outcome_status"],
        },
    }

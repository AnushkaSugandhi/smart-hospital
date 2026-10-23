"""Reads active (non-superseded) snapshots and aggregates them per date."""
from collections import defaultdict

from sqlalchemy.orm import Session

from app.core.config import CAPACITY
from app.db.models import OPTIONAL_RESOURCE_COLUMNS, ResourceSnapshot
from app.seed.generate_data import SNAPSHOTS

ALL_DEPARTMENTS = "All departments"

_SUM = {"admissions", "emergency_cases",
        "ventilators_total", "ventilators_in_use", "ot_total", "ot_in_use",
        "nurses_on_duty", "nurses_required"} | {c for c in OPTIONAL_RESOURCE_COLUMNS if c.startswith("blood_")}
_MEAN = {"bed_occupancy", "icu_occupancy", "doctor_workload", "staff_workload"}
_MIN = {"oxygen_stock_hours"}  # the scarcest supply is what matters


def active_query(db: Session, department: str | None = None):
    q = db.query(ResourceSnapshot).filter(ResourceSnapshot.superseded_by_batch.is_(None))
    if department and department != ALL_DEPARTMENTS:
        q = q.filter(ResourceSnapshot.department == department)
    return q


def departments(db: Session) -> list[str]:
    try:
        rows = active_query(db).with_entities(ResourceSnapshot.department).distinct().all()
        return sorted(r[0] for r in rows)
    except Exception:
        return ["Emergency"]


def _aggregate(rows: list[dict]) -> dict:
    out = {"date": rows[0]["date"]}
    depts = sorted({r.get("department", "Emergency") for r in rows})
    out["department"] = depts[0] if len(depts) == 1 else ALL_DEPARTMENTS
    for key in _SUM | _MEAN | _MIN:
        values = [float(r[key]) for r in rows if r.get(key) is not None]
        if not values:
            out[key] = None
        elif key in _SUM:
            out[key] = sum(values)
        elif key in _MIN:
            out[key] = min(values)
        else:
            out[key] = round(sum(values) / len(values), 4)
    # Occupancy is snapped to whole beds so every chart, forecast and alert
    # agrees with the counts on the cards (e.g. ICU 0.728 -> 15/20 -> 0.75).
    for key, total in (("bed_occupancy", CAPACITY["beds"]), ("icu_occupancy", CAPACITY["icu"])):
        if out.get(key) is not None:
            out[key] = round(round(out[key] * total) / total, 4)
    return out


def series(db: Session | None, department: str | None = None) -> list[dict]:
    """Date-ordered daily rows; hospital-wide aggregate when no department."""
    rows = []
    if db is not None:
        try:
            rows = [r.to_dict() for r in active_query(db, department).order_by(ResourceSnapshot.date.asc()).all()]
        except Exception:
            rows = []
    if not rows:
        rows = [{**s, "department": "Emergency"} for s in SNAPSHOTS]

    by_date = defaultdict(list)
    for row in rows:
        by_date[row["date"]].append(row)
    return [_aggregate(by_date[d]) for d in sorted(by_date)]


def latest_data_timestamp(db: Session):
    try:
        row = active_query(db).order_by(ResourceSnapshot.created_at.desc()).first()
        return row.created_at if row else None
    except Exception:
        return None

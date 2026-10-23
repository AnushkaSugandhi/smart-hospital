"""Builds operational alerts: threshold, predictive (forecast) and low-stock."""
from datetime import datetime, timedelta, timezone

from app.core.config import PREDICTIVE_FULL_THRESHOLD, PREDICTIVE_WINDOW_HOURS, STATUS_BANDS
from app.db.models import AlertState
from app.services.forecast_service import forecast_values

RED = STATUS_BANDS["red_above"]
AMBER = STATUS_BANDS["green_below"]

_RULES = [
    {
        "code": "BED", "resource_type": "Beds", "block": "beds", "field": "occupancy_pct",
        "what": "Bed occupancy",
        "action": {
            "critical": "Activate the discharge lounge, expedite step-down reviews and open surge beds.",
            "warning": "Review expected discharges and bed allocation for the next 24 hours.",
        },
    },
    {
        "code": "ICU", "resource_type": "ICU", "block": "icu", "field": "occupancy_pct",
        "what": "ICU occupancy",
        "action": {
            "critical": "Review ICU step-down candidates and prepare transfer agreements.",
            "warning": "Review ICU capacity against incoming emergency demand.",
        },
    },
    {
        "code": "DOC", "resource_type": "Doctors", "block": "doctors", "field": "pressure_pct",
        "what": "Doctor workload pressure",
        "action": {
            "critical": "Call in on-call doctors and redistribute patients from overloaded teams.",
            "warning": "Review shift distribution and float pool coverage.",
        },
    },
    {
        "code": "ED", "resource_type": "Emergency", "block": "emergency", "field": "pressure_pct",
        "what": "Emergency department pressure",
        "action": {
            "critical": "Open overflow treatment bays and fast-track low-acuity patients.",
            "warning": "Alert the triage lead and monitor arrivals hourly.",
        },
    },
]


def threshold_alerts(metrics: dict, snapshot_date: str) -> list[dict]:
    """One alert per metric in the amber or red band.

    The id includes the snapshot date so an acknowledgement applies to that
    day's condition, not to every future breach of the same metric.
    """
    alerts = []
    for rule in _RULES:
        block = metrics[rule["block"]]
        value = block[rule["field"]]
        severity = block["status"]
        if severity == "normal":
            continue
        band = f"above {RED:g}%" if severity == "critical" else f"between {AMBER:g}% and {RED:g}%"
        alerts.append({
            "id": f"{rule['code']}-{snapshot_date}",
            "code": rule["code"],
            "kind": "threshold",
            "severity": severity,
            "resource_type": rule["resource_type"],
            "value": value,
            "reason": f"{rule['what']} is {value}% ({band}). {block['formula']}.",
            "suggested_action": rule["action"][severity],
        })
    alerts.sort(key=lambda a: (a["severity"] != "critical", -a["value"]))
    return alerts


def _now_utc_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hours_until(current: float, forecast: list[float], threshold: float) -> float | None:
    """Hours until a daily forecast first crosses `threshold` (linear between days)."""
    points = [current] + list(forecast)
    for i in range(1, len(points)):
        if points[i] >= threshold:
            rise = points[i] - points[i - 1]
            frac = (threshold - points[i - 1]) / rise if rise > 0 else 0
            return round(24 * (i - 1 + max(min(frac, 1), 0)), 1)
    return None


def _humanize_hours(hours: float) -> str:
    if hours < 1:
        return "under an hour"
    if hours < 36:
        return f"about {round(hours)} hours"
    return f"about {round(hours / 24, 1):g} days"


_PREDICTIVE = [
    ("ICU", "icu_occupancy", "ICU", "Pre-book step-down beds and confirm ICU transfer agreements now."),
    ("BED", "bed_occupancy", "Beds", "Schedule early discharges and prepare surge ward beds."),
]


def predictive_alerts(rows: list[dict], snapshot_date: str) -> list[dict]:
    """Forecast occupancy and warn when it is likely to reach 'full' soon."""
    threshold = PREDICTIVE_FULL_THRESHOLD
    alerts = []
    for code, key, resource, action in _PREDICTIVE:
        values = [float(r[key]) for r in rows if r.get(key) is not None]
        if len(values) < 5 or values[-1] >= threshold:
            continue  # not enough history, or already full (threshold alert covers it)
        try:
            result = forecast_values(values, max(1, int(PREDICTIVE_WINDOW_HOURS // 24)))
        except Exception:
            continue
        hours = hours_until(values[-1], result["forecast"], threshold)
        if hours is None or hours > PREDICTIVE_WINDOW_HOURS:
            continue
        when = _humanize_hours(hours)
        alerts.append({
            "id": f"{code}-FORECAST-{snapshot_date}",
            "code": f"{code}-FORECAST",
            "kind": "predictive",
            "severity": "critical" if hours <= 24 else "warning",
            "resource_type": resource,
            "value": round(values[-1] * 100, 1),
            "hours_until_full": hours,
            "reason": (
                f"{resource} likely full in {when}: occupancy is {values[-1] * 100:.1f}% and the "
                f"{result['method'].replace('_', ' ')} forecast reaches {threshold * 100:g}% within "
                f"{PREDICTIVE_WINDOW_HOURS} hours."
            ),
            "suggested_action": action,
            "forecast": result["forecast"],
        })
    return alerts


def stock_alerts(cards: list[dict], snapshot_date: str) -> list[dict]:
    alerts = []
    for card in cards:
        if not card.get("available") or not card.get("low_stock"):
            continue
        alerts.append({
            "id": f"RES-{card['key'].upper()}-{card.get('as_of', snapshot_date)}",
            "code": f"RES-{card['key'].upper()}",
            "kind": "stock",
            "severity": card["status"] if card["status"] != "normal" else "warning",
            "resource_type": card["label"],
            "value": card["value"],
            "reason": f"{card['warning'] or card['label'] + ' is low'}. {card['formula']}.",
            "suggested_action": f"Replenish {card['label'].lower()} or arrange transfer from a partner facility.",
        })
    return alerts


def apply_state(db, alerts: list[dict], include_all: bool = False) -> list[dict]:
    """Merge persisted acknowledge/snooze state; hide handled alerts unless include_all."""
    ids = [a["id"] for a in alerts]
    states = {}
    if ids:
        try:
            states = {s.item_id: s for s in db.query(AlertState).filter(AlertState.item_id.in_(ids)).all()}
        except Exception:
            states = {}
    now = _now_utc_naive()
    visible = []
    for alert in alerts:
        st = states.get(alert["id"])
        alert["state"] = "active"
        if st and st.status == "acknowledged":
            alert.update(state="acknowledged", handled_by=st.updated_by,
                         handled_at=st.updated_at.isoformat() if st.updated_at else None)
        elif st and st.status == "snoozed" and st.snoozed_until and st.snoozed_until.replace(tzinfo=None) > now:
            alert.update(state="snoozed", handled_by=st.updated_by, snoozed_until=st.snoozed_until.isoformat())
        if include_all or alert["state"] == "active":
            visible.append(alert)
    return visible


def set_state(db, item_id: str, status: str, user, minutes: int | None = None, note: str | None = None) -> AlertState:
    st = db.query(AlertState).filter(AlertState.item_id == item_id).first()
    if not st:
        st = AlertState(item_id=item_id, status=status)
        db.add(st)
    st.status = status
    st.updated_by = user.username
    st.updated_at = _now_utc_naive()
    st.snoozed_until = _now_utc_naive() + timedelta(minutes=minutes) if minutes else None
    st.note = note
    db.commit()
    db.refresh(st)
    return st

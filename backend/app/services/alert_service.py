"""Builds operational alerts from the shared threshold rule."""
from app.core.config import STATUS_BANDS

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

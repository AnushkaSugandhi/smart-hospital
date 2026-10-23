"""Turns a raw resource snapshot into display-ready metric blocks.

Percentages are always computed from the same integer counts that are shown to
the user, so "5 available of 20" and "75.0%" can never disagree.
"""
from app.core.config import (
    CAPACITY,
    DOCTOR_MAX_LOAD,
    DOCTOR_SAFE_LOAD,
    METRICS,
    STAFF_MAX_LOAD,
    STATUS_META,
    status_for_pct,
)


def _status_fields(pct: float) -> dict:
    status = status_for_pct(pct)
    return {"status": status, "status_label": STATUS_META[status]["label"]}


def occupancy_block(ratio: float, total: int, metric_key: str) -> dict:
    occupied = min(max(round(total * float(ratio)), 0), total)
    pct = round(occupied / total * 100, 1) if total else 0.0
    return {
        "total": total,
        "occupied": occupied,
        "available": total - occupied,
        "occupancy_pct": pct,
        "unit": METRICS[metric_key]["unit"],
        "formula": f"{occupied} occupied ÷ {total} total × 100 = {pct}%",
        **_status_fields(pct),
    }


def doctors_block(avg_load: float, total: int = CAPACITY["doctors"]) -> dict:
    avg_load = float(avg_load)
    share = (avg_load - DOCTOR_SAFE_LOAD) / (DOCTOR_MAX_LOAD - DOCTOR_SAFE_LOAD)
    overloaded = round(total * min(max(share, 0), 1))
    pressure = round(min(avg_load / DOCTOR_MAX_LOAD * 100, 100), 1)
    return {
        "total": total,
        "available": total - overloaded,
        "overloaded": overloaded,
        "overloaded_is_estimate": True,
        "average_patients_per_doctor": round(avg_load, 2),
        "pressure_pct": pressure,
        "unit": METRICS["doctor_workload"]["unit"],
        "formula": (
            f"{avg_load:g} patients per doctor ÷ {DOCTOR_MAX_LOAD:g} max × 100 = {pressure}% pressure. "
            f"Overloaded (est.) = {total} doctors × share of load between "
            f"{DOCTOR_SAFE_LOAD:g} and {DOCTOR_MAX_LOAD:g} = {overloaded}"
        ),
        **_status_fields(pressure),
    }


def staff_block(avg_load: float) -> dict:
    avg_load = float(avg_load)
    pressure = round(min(avg_load / STAFF_MAX_LOAD * 100, 100), 1)
    return {
        "average_patients_per_staff": round(avg_load, 2),
        "pressure_pct": pressure,
        "unit": METRICS["staff_workload"]["unit"],
        "formula": f"{avg_load:g} patients per staff ÷ {STAFF_MAX_LOAD:g} max × 100 = {pressure}% pressure",
        **_status_fields(pressure),
    }


def emergency_block(active_cases: float, bays: int = CAPACITY["ed_bays"]) -> dict:
    cases = float(active_cases)
    pressure = round(min(cases / bays * 100, 100), 1)
    return {
        "active_cases": int(cases) if cases.is_integer() else cases,
        "capacity": bays,
        "pressure_pct": pressure,
        "unit": METRICS["emergency_cases"]["unit"],
        "formula": f"{cases:g} active cases ÷ {bays} ED treatment bays × 100 = {pressure}% pressure",
        **_status_fields(pressure),
    }


def core_metrics(snapshot: dict) -> dict:
    return {
        "beds": occupancy_block(snapshot["bed_occupancy"], CAPACITY["beds"], "bed_occupancy"),
        "icu": occupancy_block(snapshot["icu_occupancy"], CAPACITY["icu"], "icu_occupancy"),
        "doctors": doctors_block(snapshot["doctor_workload"]),
        "staff": staff_block(snapshot["staff_workload"]),
        "emergency": emergency_block(snapshot["emergency_cases"]),
    }

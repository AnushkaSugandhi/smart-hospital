from app.core.config import (
    DOCTOR_MAX_LOAD,
    OCCUPANCY_REFERENCE,
    RISK_FACTORS,
    STAFF_MAX_LOAD,
    risk_level_for,
)


def factor_pressures(
    bed_occupancy: float,
    icu_occupancy: float,
    doctor_workload: float,
    staff_workload: float,
    emergency_pressure: float,
) -> dict:
    """Normalise each input onto a 0-100 pressure scale."""
    return {
        "beds": min((bed_occupancy / OCCUPANCY_REFERENCE) * 100, 100),
        "icu": min((icu_occupancy / OCCUPANCY_REFERENCE) * 100, 100),
        "doctors": min((doctor_workload / DOCTOR_MAX_LOAD) * 100, 100),
        "staff": min((staff_workload / STAFF_MAX_LOAD) * 100, 100),
        "emergency": min(emergency_pressure, 100),
    }


def calculate_risk_score(
    bed_occupancy: float,
    icu_occupancy: float,
    doctor_workload: float,
    staff_workload: float,
    emergency_pressure: float,
) -> dict:
    pressures = factor_pressures(
        bed_occupancy, icu_occupancy, doctor_workload, staff_workload, emergency_pressure
    )

    breakdown = []
    for factor in RISK_FACTORS:
        pressure = max(pressures[factor["key"]], 0)
        contribution = pressure * factor["weight"]
        breakdown.append({
            "key": factor["key"],
            "label": factor["label"],
            "pressure": round(pressure, 1),
            "weight": factor["weight"],
            "contribution": round(contribution, 1),
            "formula": factor["formula"],
        })

    score = round(min(max(sum(b["contribution"] for b in breakdown), 0), 100), 1)
    level, level_label = risk_level_for(score)
    breakdown.sort(key=lambda b: b["contribution"], reverse=True)

    return {
        "score": score,
        "scale": {"min": 0, "max": 100},
        "level": level,
        "level_label": level_label,
        "label": "Operational resource-risk indicator",
        "breakdown": breakdown,
        "top_driver": breakdown[0]["label"],
    }

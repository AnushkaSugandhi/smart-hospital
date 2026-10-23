def calculate_risk_score(
    bed_occupancy: float,
    icu_occupancy: float,
    doctor_workload: float,
    staff_workload: float,
    emergency_pressure: float,
) -> dict:
    bed_pressure = min((bed_occupancy / 0.90) * 100, 100)
    icu_pressure = min((icu_occupancy / 0.90) * 100, 100)
    doctor_pressure = min((doctor_workload / 15) * 100, 100)
    staff_pressure = min((staff_workload / 12) * 100, 100)

    score = (
        bed_pressure * 0.25
        + icu_pressure * 0.20
        + doctor_pressure * 0.20
        + staff_pressure * 0.15
        + emergency_pressure * 0.20
    )
    score = round(score, 1)

    if score >= 81:
        level = "critical"
    elif score >= 61:
        level = "high"
    elif score >= 31:
        level = "moderate"
    else:
        level = "low"

    return {
        "score": score,
        "level": level,
        "label": "Operational resource-risk indicator",
    }

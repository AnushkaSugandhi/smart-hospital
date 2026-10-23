def simulate_scenario(
    baseline: dict,
    admissions_change_pct: float,
    emergency_cases_change_pct: float = 0,
    available_beds_change_pct: float = 0,
    icu_capacity_change_pct: float = 0,
    doctor_availability_change_pct: float = 0,
    staff_availability_change_pct: float = 0,
) -> dict:
    bed = baseline["bed_occupancy_pct"]
    icu = baseline["icu_occupancy_pct"]
    doctor = baseline["doctor_workload"]

    simulated_bed = (
        bed
        + admissions_change_pct * 0.21
        + emergency_cases_change_pct * 0.05
        - available_beds_change_pct * 0.30
    )
    simulated_icu = (
        icu
        + admissions_change_pct * 0.34
        + emergency_cases_change_pct * 0.12
        - icu_capacity_change_pct * 0.25
    )

    admission_factor = admissions_change_pct / 100
    doctor_factor = doctor_availability_change_pct / 100
    staff_factor = staff_availability_change_pct / 100

    simulated_doctor = (
        doctor * (1 + admission_factor * 0.60)
        / max(1 + doctor_factor, 0.1)
    )
    simulated_staff = (
        baseline["staff_workload"]
        * (1 + admission_factor * 0.45)
        / max(1 + staff_factor, 0.1)
    )

    risk_score = (
        simulated_bed * 0.30
        + simulated_icu * 0.30
        + min(simulated_doctor / 15 * 100, 100) * 0.20
        + min(simulated_staff / 12 * 100, 100) * 0.10
        + min(
            baseline["emergency_pressure_pct"]
            * (1 + emergency_cases_change_pct / 100),
            100,
        ) * 0.10
    )

    risk_score = round(min(max(risk_score, 0), 100), 1)

    if risk_score >= 81:
        level = "critical"
    elif risk_score >= 61:
        level = "high"
    elif risk_score >= 31:
        level = "moderate"
    else:
        level = "low"

    return {
        "bed_occupancy_pct": round(max(simulated_bed, 0), 2),
        "icu_occupancy_pct": round(max(simulated_icu, 0), 2),
        "doctor_workload": round(max(simulated_doctor, 0), 2),
        "staff_workload": round(max(simulated_staff, 0), 2),
        "risk_score": risk_score,
        "risk_level": level,
    }

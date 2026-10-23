"""Top 'What should I do now?' actions, each with a simulated impact."""
from app.core.config import STATUS_BANDS
from app.services.simulation_service import simulate_scenario

_PLAYBOOK = {
    "beds": {
        "title": "Open 10% more beds via early discharges and the surge ward",
        "scenario": {"available_beds_change_pct": 10},
    },
    "icu": {
        "title": "Free ICU capacity by stepping down stable patients",
        "scenario": {"icu_capacity_change_pct": 10},
    },
    "doctors": {
        "title": "Call in on-call doctors (+10% doctor availability)",
        "scenario": {"doctor_availability_change_pct": 10},
    },
    "staff": {
        "title": "Bring in float-pool nurses and staff (+10%)",
        "scenario": {"staff_availability_change_pct": 10},
    },
    "emergency": {
        "title": "Fast-track low-acuity emergency patients (−15% ED load)",
        "scenario": {"emergency_cases_change_pct": -15},
    },
}


def baseline_from_state(state: dict) -> dict:
    return {
        "bed_occupancy_pct": state["beds"]["occupancy_pct"],
        "icu_occupancy_pct": state["icu"]["occupancy_pct"],
        "doctor_workload": state["doctors"]["average_patients_per_doctor"],
        "staff_workload": state["staff"]["average_patients_per_staff"],
        "emergency_pressure_pct": state["emergency"]["pressure_pct"],
    }


def next_actions(state: dict, alerts: list[dict], limit: int = 3) -> list[dict]:
    baseline = baseline_from_state(state)
    base_risk = simulate_scenario(baseline, 0)["risk_score"]
    predicted = {a["resource_type"]: a for a in alerts if a.get("kind") == "predictive"}

    actions = []
    for factor in state["risk"]["breakdown"]:
        if factor["pressure"] < STATUS_BANDS["green_below"]:
            continue
        play = _PLAYBOOK[factor["key"]]
        scenario = simulate_scenario(baseline, 0, **play["scenario"])
        why = (f"{factor['label']} pressure is {factor['pressure']}% and adds "
               f"{factor['contribution']} points to the risk score.")
        forecast_alert = predicted.get("ICU" if factor["key"] == "icu" else "Beds" if factor["key"] == "beds" else "")
        if forecast_alert:
            why += f" {forecast_alert['reason'].split(':')[0]}."
        delta = round(scenario["risk_score"] - base_risk, 1)
        actions.append({
            "id": f"REC-{factor['key']}-{state['date']}",
            "factor": factor["key"],
            "title": play["title"],
            "why": why,
            "impact": f"Estimated risk {base_risk} → {scenario['risk_score']} ({delta:+g} points)",
            "risk_before": base_risk,
            "risk_after": scenario["risk_score"],
            "scenario": play["scenario"],
            "priority": factor["contribution"],
        })
    actions.sort(key=lambda a: a["priority"], reverse=True)
    return actions[:limit]

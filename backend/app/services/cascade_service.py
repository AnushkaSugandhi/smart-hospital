DEPENDENCIES = [
    {
        "source": "admissions",
        "target": "bed_demand",
        "factor": 0.75,
        "reason": "Admissions increase expected bed demand.",
    },
    {
        "source": "bed_demand",
        "target": "bed_occupancy",
        "factor": 0.90,
        "reason": "Higher bed demand raises occupancy.",
    },
    {
        "source": "bed_occupancy",
        "target": "icu_pressure",
        "factor": 0.20,
        "reason": "High occupancy increases ICU pressure.",
    },
    {
        "source": "admissions",
        "target": "doctor_workload",
        "factor": 0.60,
        "reason": "Higher demand increases doctor workload.",
    },
    {
        "source": "doctor_workload",
        "target": "staff_workload",
        "factor": 0.50,
        "reason": "Higher doctor workload increases staff pressure.",
    },
]


def analyze_cascade(change_pct: float) -> list[dict]:
    results = []
    for dep in DEPENDENCIES:
        propagated = change_pct * dep["factor"]
        results.append({
            "source": dep["source"],
            "target": dep["target"],
            "factor": dep["factor"],
            "change_pct": round(propagated, 2),
            "reason": dep["reason"],
        })
    return results

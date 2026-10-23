FEATURES = [
    "admissions",
    "emergency_cases",
    "bed_occupancy",
    "icu_occupancy",
    "doctor_workload",
    "staff_workload",
]

WEIGHTS = {
    "admissions": 0.20,
    "emergency_cases": 0.20,
    "bed_occupancy": 0.20,
    "icu_occupancy": 0.20,
    "doctor_workload": 0.10,
    "staff_workload": 0.10,
}


def similarity_score(current: dict, historical: dict) -> float:
    distance = 0
    for feature in FEATURES:
        difference = abs(
            float(current.get(feature, 0))
            - float(historical.get(feature, 0))
        )
        distance += difference * WEIGHTS[feature]

    return max(0, round(100 - distance, 2))

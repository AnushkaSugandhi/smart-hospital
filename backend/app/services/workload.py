def classify_doctor_workload(patients_per_doctor: float) -> str:
    if patients_per_doctor > 15:
        return "overloaded"
    if patients_per_doctor >= 10:
        return "warning"
    return "normal"


def classify_staff_workload(patients_per_staff: float) -> str:
    if patients_per_staff > 12:
        return "overloaded"
    if patients_per_staff >= 8:
        return "warning"
    return "normal"

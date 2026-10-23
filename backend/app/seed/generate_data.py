from datetime import date, timedelta
import math
import random


def generate_snapshots(days: int = 30) -> list[dict]:
    random.seed(42)
    rows = []
    start = date.today() - timedelta(days=days - 1)

    for i in range(days):
        day = start + timedelta(days=i)
        seasonal = 8 if day.month in (11, 12, 1, 2) else 0
        wave = 5 * math.sin(i / 3)
        admissions = round(70 + seasonal + wave + random.uniform(-4, 4))
        emergency = round(14 + admissions * 0.06 + random.uniform(-1.5, 1.5))
        bed_occ = min(0.97, max(0.55, 0.70 + (admissions - 70) * 0.004))
        icu_occ = min(0.97, max(0.50, 0.68 + (emergency - 14) * 0.012))
        doctor = round(admissions / 6.2, 2)
        staff = round(admissions / 8.7, 2)
        rows.append({
            "date": str(day),
            "admissions": admissions,
            "emergency_cases": emergency,
            "bed_occupancy": round(bed_occ, 3),
            "icu_occupancy": round(icu_occ, 3),
            "doctor_workload": doctor,
            "staff_workload": staff,
        })

    return rows


SNAPSHOTS = generate_snapshots()

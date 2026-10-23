from datetime import date, timedelta
import math
import random

BLOOD_BASE = {"a_pos": 28, "a_neg": 9, "b_pos": 30, "b_neg": 8, "o_pos": 36, "o_neg": 11, "ab_pos": 14, "ab_neg": 6}


def generate_snapshots(days: int = 30) -> list[dict]:
    random.seed(42)
    # Separate generator for the optional resources so the core series stays
    # identical to earlier versions of the seed.
    extra = random.Random(7)
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

        nurses_required = round(48 + admissions * 0.2)
        row = {
            "date": str(day),
            "admissions": admissions,
            "emergency_cases": emergency,
            "bed_occupancy": round(bed_occ, 3),
            "icu_occupancy": round(icu_occ, 3),
            "doctor_workload": doctor,
            "staff_workload": staff,
            "ventilators_total": 24,
            "ventilators_in_use": min(24, round(24 * icu_occ * 0.8 + extra.uniform(-2, 2))),
            "ot_total": 8,
            "ot_in_use": max(0, min(8, round(4 + wave / 2 + extra.uniform(-1, 1.5)))),
            "nurses_on_duty": nurses_required - extra.choice([-2, 0, 1, 2, 3, 4]),
            "nurses_required": nurses_required,
            # Oxygen is resupplied every 5 days and drains in between.
            "oxygen_stock_hours": round(96 - (i % 5) * 16 + extra.uniform(-3, 3), 1),
        }
        for group, base in BLOOD_BASE.items():
            row[f"blood_{group}"] = max(0, round(base - (i % 7) * base * 0.06 + extra.uniform(-2, 2)))
        rows.append(row)

    return rows


SNAPSHOTS = generate_snapshots()

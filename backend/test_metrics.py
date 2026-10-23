from app.core.config import status_for_pct, risk_level_for
from app.services.metrics_service import core_metrics, occupancy_block, doctors_block
from app.services.risk_engine import calculate_risk_score
from app.services.alert_service import threshold_alerts

SNAPSHOT = {
    "date": "2026-10-23",
    "admissions": 72,
    "emergency_cases": 18,
    "bed_occupancy": 0.684,
    "icu_occupancy": 0.728,
    "doctor_workload": 11.6,
    "staff_workload": 8.3,
}


def test_icu_percentage_matches_counts():
    icu = occupancy_block(0.728, 20, "icu_occupancy")
    assert icu["occupied"] == 15
    assert icu["available"] == 5
    assert icu["occupancy_pct"] == 75.0
    assert "15 occupied ÷ 20 total" in icu["formula"]


def test_percentages_always_derive_from_counts():
    for ratio in [0.0, 0.333, 0.5, 0.684, 0.728, 0.91, 1.0]:
        for total in [20, 120]:
            b = occupancy_block(ratio, total, "bed_occupancy")
            assert b["occupied"] + b["available"] == total
            assert b["occupancy_pct"] == round(b["occupied"] / total * 100, 1)


def test_single_colour_rule():
    assert status_for_pct(68.4) == "normal"
    assert status_for_pct(70.0) == "warning"
    assert status_for_pct(75.0) == "warning"
    assert status_for_pct(85.0) == "warning"
    assert status_for_pct(85.1) == "critical"


def test_bed_and_icu_statuses_follow_rule():
    m = core_metrics(SNAPSHOT)
    assert m["beds"]["occupancy_pct"] == 68.3  # 82 of 120
    assert m["beds"]["status"] == "normal"
    assert m["icu"]["status"] == "warning"


def test_doctor_overload_is_proportional_not_all_or_nothing():
    assert doctors_block(9.0)["overloaded"] == 0
    assert doctors_block(12.5)["overloaded"] == 12  # halfway between 10 and 15
    assert doctors_block(16.0)["overloaded"] == 25
    assert doctors_block(10.4)["overloaded"] < 25


def test_emergency_pressure_states_its_denominator():
    e = core_metrics(SNAPSHOT)["emergency"]
    assert e["pressure_pct"] == 90.0
    assert e["capacity"] == 20
    assert "ED treatment bays" in e["formula"]


def test_risk_breakdown_sums_to_score():
    risk = calculate_risk_score(0.75, 0.80, 12, 9, 80)
    assert risk["scale"] == {"min": 0, "max": 100}
    assert {f["key"] for f in risk["breakdown"]} == {"beds", "icu", "doctors", "staff", "emergency"}
    assert abs(sum(f["contribution"] for f in risk["breakdown"]) - risk["score"]) < 0.5
    assert risk["level_label"] in {"Low", "Medium", "High", "Critical"}


def test_risk_levels():
    assert risk_level_for(10) == ("low", "Low")
    assert risk_level_for(45) == ("medium", "Medium")
    assert risk_level_for(70) == ("high", "High")
    assert risk_level_for(90) == ("critical", "Critical")


def test_alerts_use_shared_thresholds():
    alerts = threshold_alerts(core_metrics(SNAPSHOT), SNAPSHOT["date"])
    by_code = {a["code"]: a for a in alerts}
    assert "BED" not in by_code  # 68.3% is green
    assert by_code["ICU"]["severity"] == "warning"
    assert by_code["ED"]["severity"] == "critical"
    assert all(a["id"].endswith(SNAPSHOT["date"]) for a in alerts)

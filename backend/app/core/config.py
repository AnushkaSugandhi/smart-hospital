"""Single source of truth for thresholds, capacities, colours, units and formulas.

Every percentage, status colour and risk level shown in the UI is derived from
the values in this module. The frontend fetches them from /api/v1/config so the
two sides cannot drift apart.
"""

# Hospital capacity used to turn ratios in the snapshot table into counts.
CAPACITY = {
    "beds": 120,
    "icu": 20,
    "doctors": 25,
    "ed_bays": 20,  # emergency treatment bays; emergency pressure = active cases / bays
}

# One colour rule for every utilisation-style metric (values in percent).
STATUS_BANDS = {
    "green_below": 70.0,  # < 70  -> green / normal
    "red_above": 85.0,    # > 85  -> red / critical; 70-85 inclusive -> amber / warning
}

STATUS_META = {
    "normal": {"label": "Normal", "color": "green"},
    "warning": {"label": "Elevated", "color": "amber"},
    "critical": {"label": "Critical", "color": "red"},
}

# Workload limits; workload pressure = value / max * 100.
DOCTOR_SAFE_LOAD = 10.0   # patients per doctor considered safe
DOCTOR_MAX_LOAD = 15.0    # patients per doctor treated as 100% pressure
STAFF_MAX_LOAD = 12.0     # patients per staff member treated as 100% pressure

# Risk score: weighted sum of factor pressures, 0-100.
RISK_FACTORS = [
    {"key": "beds", "label": "Beds", "weight": 0.25,
     "formula": "bed occupancy ÷ 90% reference × 100 (capped at 100)"},
    {"key": "icu", "label": "ICU", "weight": 0.20,
     "formula": "ICU occupancy ÷ 90% reference × 100 (capped at 100)"},
    {"key": "doctors", "label": "Doctors", "weight": 0.20,
     "formula": f"patients per doctor ÷ {DOCTOR_MAX_LOAD:g} × 100 (capped at 100)"},
    {"key": "staff", "label": "Staff", "weight": 0.15,
     "formula": f"patients per staff ÷ {STAFF_MAX_LOAD:g} × 100 (capped at 100)"},
    {"key": "emergency", "label": "Emergency", "weight": 0.20,
     "formula": f"active emergency cases ÷ {CAPACITY['ed_bays']} ED bays × 100 (capped at 100)"},
]
OCCUPANCY_REFERENCE = 0.90

# Lower bound (inclusive) of each risk level, highest first.
RISK_LEVELS = [
    (81, "critical", "Critical"),
    (61, "high", "High"),
    (31, "medium", "Medium"),
    (0, "low", "Low"),
]

# Additional resources (optional upload columns).
# Supply-type metrics (lower is worse) use their own floors rather than the
# utilisation bands above.
LOW_STOCK = {
    "oxygen_hours_warning": 24.0,
    "oxygen_hours_critical": 12.0,
    "blood_units_warning": 10,
    "blood_units_critical": 5,
    "nurse_coverage_warning_below": 100.0,  # % of required nurses on duty
    "nurse_coverage_critical_below": 90.0,
}
BLOOD_GROUPS = ["a_pos", "a_neg", "b_pos", "b_neg", "o_pos", "o_neg", "ab_pos", "ab_neg"]

# Predictive alerts fire when a forecast crosses this occupancy within the window.
PREDICTIVE_FULL_THRESHOLD = 0.95
PREDICTIVE_WINDOW_HOURS = 72

# Units, plain-language descriptions and formulas for every KPI.
METRICS = {
    "bed_occupancy": {
        "label": "Bed occupancy", "unit": "%",
        "description": "Share of inpatient beds currently occupied.",
        "formula": f"occupied beds ÷ total beds ({CAPACITY['beds']}) × 100",
        "higher_is_worse": True,
    },
    "icu_occupancy": {
        "label": "ICU occupancy", "unit": "%",
        "description": "Share of ICU beds currently occupied.",
        "formula": f"occupied ICU beds ÷ total ICU beds ({CAPACITY['icu']}) × 100",
        "higher_is_worse": True,
    },
    "doctor_workload": {
        "label": "Doctor workload", "unit": "patients per doctor",
        "description": "Average number of active patients each on-duty doctor is responsible for.",
        "formula": (
            f"pressure = patients per doctor ÷ {DOCTOR_MAX_LOAD:g} × 100. Overloaded doctors are estimated "
            f"assuming load spreads evenly between {DOCTOR_SAFE_LOAD:g} (safe) and {DOCTOR_MAX_LOAD:g} (max)."
        ),
        "higher_is_worse": True,
    },
    "staff_workload": {
        "label": "Staff workload", "unit": "patients per staff",
        "description": "Average number of patients per nursing/clinical staff member.",
        "formula": f"pressure = patients per staff ÷ {STAFF_MAX_LOAD:g} × 100",
        "higher_is_worse": True,
    },
    "emergency_cases": {
        "label": "Emergency cases", "unit": "active cases",
        "description": "Patients currently being treated in the emergency department.",
        "formula": f"pressure = active cases ÷ {CAPACITY['ed_bays']} ED treatment bays × 100 (capped at 100)",
        "higher_is_worse": True,
    },
    "admissions": {
        "label": "Admissions", "unit": "patients per day",
        "description": "New inpatient admissions recorded for the day.",
        "formula": "count of admissions in the daily snapshot",
        "higher_is_worse": True,
    },
    "risk_score": {
        "label": "Resource risk", "unit": "score 0-100",
        "description": "Composite operational risk across beds, ICU, doctors, staff and emergency.",
        "formula": " + ".join(f"{f['label']} × {f['weight']:.2f}" for f in RISK_FACTORS),
        "higher_is_worse": True,
    },
}


def status_for_pct(pct: float) -> str:
    """Map a 0-100 percentage onto the shared green/amber/red rule."""
    if pct > STATUS_BANDS["red_above"]:
        return "critical"
    if pct >= STATUS_BANDS["green_below"]:
        return "warning"
    return "normal"


def risk_level_for(score: float) -> tuple[str, str]:
    for lower, key, label in RISK_LEVELS:
        if score >= lower:
            return key, label
    return "low", "Low"


def public_config() -> dict:
    """Everything the frontend needs to render colours, units and tooltips."""
    return {
        "capacity": CAPACITY,
        "status_bands": STATUS_BANDS,
        "status_meta": STATUS_META,
        "risk_levels": [{"min": lo, "key": k, "label": lbl} for lo, k, lbl in RISK_LEVELS],
        "risk_factors": RISK_FACTORS,
        "metrics": METRICS,
        "low_stock": LOW_STOCK,
        "blood_groups": BLOOD_GROUPS,
        "doctor_safe_load": DOCTOR_SAFE_LOAD,
        "doctor_max_load": DOCTOR_MAX_LOAD,
        "staff_max_load": STAFF_MAX_LOAD,
    }

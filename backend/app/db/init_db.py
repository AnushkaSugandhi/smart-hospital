import logging
from sqlalchemy import inspect, text
from app.core.security import hash_password, is_hashed, normalize_role
from app.db.database import Base, engine, SessionLocal
from app.db.models import (
    OPTIONAL_RESOURCE_COLUMNS,
    User,
    Department,
    Patient,
    Doctor,
    Staff,
    Bed,
    ResourceSnapshot,
    HistoricalEvent,
    ForecastRecord,
    AlertRecord,
    RecommendationRecord,
    DecisionRecord,
    DecisionOutcome,
)
from app.seed.generate_data import generate_snapshots

logger = logging.getLogger("smart_hospital.init_db")


DEMO_USERS = [
    # username, password, role, full name
    ("admin", "admin123", "Admin", "Operations Command Director"),
    ("analyst", "analyst123", "Analyst", "Capacity Planning Analyst"),
    ("viewer", "viewer123", "Viewer", "Ward Coordinator"),
]


def migrate_columns():
    """Add columns that exist on models but not yet in the database.

    create_all() only creates missing tables, so existing PostgreSQL/SQLite
    databases need this for new nullable columns.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            present = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in present:
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN {column.name} {col_type}'))
                logger.info("Added column %s.%s", table.name, column.name)


def secure_users(db):
    """Hash any plaintext passwords, map legacy roles, ensure demo role users."""
    for user in db.query(User).all():
        if not is_hashed(user.password_hash):
            user.password_hash = hash_password(user.password_hash)
        user.role = normalize_role(user.role)
    existing = {u.username for u in db.query(User).all()}
    for username, password, role, full_name in DEMO_USERS:
        if username not in existing:
            db.add(User(username=username, email=f"{username}@vgh.hospital",
                        password_hash=hash_password(password), role=role, full_name=full_name))
    db.commit()


def init_database():
    """Create tables, migrate new columns and seed initial records if empty."""
    Base.metadata.create_all(bind=engine)
    migrate_columns()
    db = SessionLocal()
    try:
        # 1. Departments
        if db.query(Department).count() == 0:
            departments = [
                Department(name="Emergency Department", code="ED", total_beds=40, total_icu=8, total_doctors=10, total_staff=18),
                Department(name="Intensive Care Unit", code="ICU", total_beds=20, total_icu=20, total_doctors=6, total_staff=12),
                Department(name="General Medicine", code="GM", total_beds=45, total_icu=0, total_doctors=6, total_staff=8),
                Department(name="Surgical Inpatient", code="SURG", total_beds=35, total_icu=4, total_doctors=5, total_staff=7),
            ]
            db.add_all(departments)
            db.commit()

        # 2. Users
        if db.query(User).count() == 0:
            db.add(User(username="cmo", email="cmo@vgh.hospital", password_hash=hash_password("admin123"),
                        role="Analyst", full_name="Dr. Sarah Chen"))
            db.commit()
        secure_users(db)

        # 3. Doctors
        if db.query(Doctor).count() == 0:
            doctors = [
                Doctor(doctor_id="DOC-101", name="Dr. Marcus Vance", specialty="Emergency Medicine", department="Emergency", shift_status="On-Duty", active_patients=12, workload_score=11.4),
                Doctor(doctor_id="DOC-102", name="Dr. Priya Patel", specialty="Critical Care / ICU", department="ICU", shift_status="On-Duty", active_patients=9, workload_score=10.8),
                Doctor(doctor_id="DOC-103", name="Dr. Alex Rivera", specialty="Internal Medicine", department="Emergency", shift_status="On-Duty", active_patients=11, workload_score=10.5),
                Doctor(doctor_id="DOC-104", name="Dr. Elena Rostova", specialty="General Surgery", department="Emergency", shift_status="On-Call", active_patients=4, workload_score=6.2),
            ]
            db.add_all(doctors)
            db.commit()

        # 4. Staff
        if db.query(Staff).count() == 0:
            staff_list = [
                Staff(staff_id="STF-201", name="Nurse Supervisor Karen Ross", role="Charge Nurse", department="Emergency", shift="Morning", workload_score=9.1),
                Staff(staff_id="STF-202", name="Nurse David Kim", role="Triage Registered Nurse", department="Emergency", shift="Morning", workload_score=8.7),
                Staff(staff_id="STF-203", name="Nurse Maria Santos", role="ICU Staff Nurse", department="ICU", shift="Day", workload_score=8.4),
            ]
            db.add_all(staff_list)
            db.commit()

        # 5. Beds
        if db.query(Bed).count() == 0:
            beds = [
                Bed(bed_number="ED-01", department="Emergency", bed_type="Regular", is_occupied=True, patient_id="PT-901"),
                Bed(bed_number="ED-02", department="Emergency", bed_type="Regular", is_occupied=True, patient_id="PT-902"),
                Bed(bed_number="ED-03", department="Emergency", bed_type="Regular", is_occupied=False, patient_id=None),
                Bed(bed_number="ICU-01", department="Emergency", bed_type="ICU", is_occupied=True, patient_id="PT-903"),
                Bed(bed_number="ICU-02", department="Emergency", bed_type="ICU", is_occupied=False, patient_id=None),
            ]
            db.add_all(beds)
            db.commit()

        # 6. Patients
        if db.query(Patient).count() == 0:
            patients = [
                Patient(patient_id="PT-901", name="Arthur Pendelton", age=68, gender="Male", department="Emergency", triage_priority="Level 2 - Emergent", admission_date="2026-10-22", status="Admitted", bed_assigned="ED-01"),
                Patient(patient_id="PT-902", name="Clara Oswald", age=42, gender="Female", department="Emergency", triage_priority="Level 3 - Urgent", admission_date="2026-10-23", status="Admitted", bed_assigned="ED-02"),
                Patient(patient_id="PT-903", name="Harold Finch", age=74, gender="Male", department="ICU", triage_priority="Level 1 - Resuscitation", admission_date="2026-10-23", status="Admitted", bed_assigned="ICU-01"),
            ]
            db.add_all(patients)
            db.commit()

        # 7. Resource Snapshots (30 days)
        if db.query(ResourceSnapshot).count() == 0:
            snapshots = generate_snapshots(30)
            for s in snapshots:
                db.add(ResourceSnapshot(
                    date=s["date"],
                    department="Emergency",
                    admissions=float(s["admissions"]),
                    emergency_cases=float(s["emergency_cases"]),
                    bed_occupancy=float(s["bed_occupancy"]),
                    icu_occupancy=float(s["icu_occupancy"]),
                    doctor_workload=float(s["doctor_workload"]),
                    staff_workload=float(s["staff_workload"]),
                    **{c: float(s[c]) for c in OPTIONAL_RESOURCE_COLUMNS if s.get(c) is not None},
                ))
            db.commit()

        # 8. Historical Events
        if db.query(HistoricalEvent).count() == 0:
            events = [
                HistoricalEvent(
                    date="2025-12-14",
                    department="Emergency",
                    situation="Respiratory admissions increased due to seasonal influx.",
                    admissions=80.0,
                    emergency_cases=18.0,
                    bed_occupancy=0.90,
                    icu_occupancy=0.86,
                    doctor_workload=12.5,
                    staff_workload=9.2,
                    previous_action="Two compatible doctors were reassigned from non-acute clinics.",
                    outcome="Emergency backlog decreased within two days without adverse incidents.",
                    outcome_status="resolved",
                ),
                HistoricalEvent(
                    date="2026-01-08",
                    department="Emergency",
                    situation="Emergency surge with high bed occupancy following cold snap.",
                    admissions=76.0,
                    emergency_cases=17.0,
                    bed_occupancy=0.88,
                    icu_occupancy=0.82,
                    doctor_workload=12.1,
                    staff_workload=8.8,
                    previous_action="Bed allocation was reviewed and discharge lounge activated.",
                    outcome="Occupancy stabilized after three days with reduced boarder wait times.",
                    outcome_status="resolved",
                ),
            ]
            db.add_all(events)
            db.commit()

        # 9. Forecasts
        if db.query(ForecastRecord).count() == 0:
            db.add(ForecastRecord(
                generated_date="2026-10-23",
                metric="admissions",
                horizon_days=7,
                forecasted_values="[82, 84, 85, 87, 86, 83, 81]",
                method="Autoregressive Moving Trend",
                quality_score="High (MAPE < 5.4%)",
            ))
            db.commit()

        # 10. Alerts
        if db.query(AlertRecord).count() == 0:
            alerts = [
                AlertRecord(alert_code="BED-001", department="Emergency", severity="critical", resource_type="Beds", reason="Bed occupancy is above 80% operational buffer threshold.", suggested_action="Review step-down beds and activate discharge lounge.", is_active=True),
                AlertRecord(alert_code="DOC-001", department="Emergency", severity="warning", resource_type="Doctors", reason="Average physician patient load is elevated above 10 pts/dr.", suggested_action="Review on-call schedule and reassign float staff.", is_active=True),
            ]
            db.add_all(alerts)
            db.commit()

        # 11. Recommendations
        if db.query(RecommendationRecord).count() == 0:
            recs = [
                RecommendationRecord(
                    department="Emergency",
                    trigger_condition="Bed Occupancy > 80% & ICU Occupancy > 75%",
                    recommendation_text="Activate expedited step-down protocol and prepare surge bed ward B.",
                    rationale="Mitigates emergency boarding wait times and prevents diversion.",
                    status="Active",
                )
            ]
            db.add_all(recs)
            db.commit()

        # 12. Decisions
        if db.query(DecisionRecord).count() == 0:
            dec = DecisionRecord(
                department="Emergency",
                issue="Elevated bed occupancy exceeding 85% threshold",
                recommendation="Expedite step-down patient reviews and notify float nurse pool.",
                administrator_action="Authorized expedited step-down discharges and placed nurse pool on 1-hour standby.",
                outcome="resolved",
                outcome_details="Bed occupancy normalized to 78% within 36 hours.",
                recorded_by="Dr. Sarah Chen (Chief Medical Officer)",
            )
            db.add(dec)
            db.commit()
            db.refresh(dec)

            # 13. Decision Outcomes
            db.add(DecisionOutcome(
                decision_id=dec.id,
                bed_occupancy_delta=-0.08,
                icu_occupancy_delta=-0.04,
                risk_score_delta=-12.5,
                evaluation_summary="Expedited discharge initiative reduced average ED boarding time by 34 minutes.",
                status="stabilized",
            ))
            db.commit()

    finally:
        db.close()

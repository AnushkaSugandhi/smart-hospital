import logging
from app.db.database import Base, engine, SessionLocal
from app.db.models import ResourceSnapshot, HistoricalEvent, User, DecisionRecord
from app.seed.generate_data import generate_snapshots

logger = logging.getLogger("smart_hospital.init_db")

INITIAL_HISTORICAL_EVENTS = [
    {
        "date": "2025-12-14",
        "department": "Emergency",
        "situation": "Respiratory admissions increased due to seasonal influx.",
        "admissions": 80.0,
        "emergency_cases": 18.0,
        "bed_occupancy": 0.90,
        "icu_occupancy": 0.86,
        "doctor_workload": 12.5,
        "staff_workload": 9.2,
        "previous_action": "Two compatible doctors were reassigned from non-acute clinics.",
        "outcome": "Emergency backlog decreased within two days without adverse incidents.",
        "outcome_status": "resolved",
    },
    {
        "date": "2026-01-08",
        "department": "Emergency",
        "situation": "Emergency surge with high bed occupancy following cold snap.",
        "admissions": 76.0,
        "emergency_cases": 17.0,
        "bed_occupancy": 0.88,
        "icu_occupancy": 0.82,
        "doctor_workload": 12.1,
        "staff_workload": 8.8,
        "previous_action": "Bed allocation was reviewed and discharge lounge activated.",
        "outcome": "Occupancy stabilized after three days with reduced boarder wait times.",
        "outcome_status": "resolved",
    },
    {
        "date": "2026-02-19",
        "department": "Emergency",
        "situation": "Sudden ICU occupancy spike with critical trauma transfers.",
        "admissions": 74.0,
        "emergency_cases": 21.0,
        "bed_occupancy": 0.85,
        "icu_occupancy": 0.95,
        "doctor_workload": 11.8,
        "staff_workload": 9.0,
        "previous_action": "Step-down beds prepared and mutual aid protocol placed on standby.",
        "outcome": "All high-acuity patients safely accommodated with zero diversion hours.",
        "outcome_status": "resolved",
    },
]

INITIAL_DECISIONS = [
    {
        "department": "Emergency",
        "issue": "Elevated bed occupancy exceeding 85% threshold",
        "recommendation": "Expedite step-down patient reviews and notify float nurse pool.",
        "administrator_action": "Authorized expedited step-down discharges and placed nurse pool on 1-hour standby.",
        "outcome": "resolved",
        "outcome_details": "Bed occupancy normalized to 78% within 36 hours.",
        "recorded_by": "Dr. Sarah Chen (Chief Medical Officer)",
    }
]


def init_database():
    """Create all tables and seed initial data if empty."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Seed ResourceSnapshots if empty
        if db.query(ResourceSnapshot).count() == 0:
            logger.info("Seeding resource snapshots...")
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
                ))
            db.commit()

        # Seed HistoricalEvents if empty
        if db.query(HistoricalEvent).count() == 0:
            logger.info("Seeding historical events...")
            for event in INITIAL_HISTORICAL_EVENTS:
                db.add(HistoricalEvent(**event))
            db.commit()

        # Seed initial Decisions if empty
        if db.query(DecisionRecord).count() == 0:
            logger.info("Seeding initial decision record...")
            for dec in INITIAL_DECISIONS:
                db.add(DecisionRecord(**dec))
            db.commit()

        # Seed initial User if empty
        if db.query(User).count() == 0:
            logger.info("Creating default administrator user...")
            # Simple demo hash for 'admin123'
            db.add(User(
                username="admin",
                password_hash="admin123",
                role="Administrator",
                full_name="Operations Command Admin",
            ))
            db.commit()

    finally:
        db.close()

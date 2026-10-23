from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from app.db.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class ResourceSnapshot(Base):
    __tablename__ = "resource_snapshots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    date = Column(String(50), index=True, nullable=False)
    department = Column(String(100), default="Emergency", nullable=False)
    admissions = Column(Float, nullable=False)
    emergency_cases = Column(Float, nullable=False)
    bed_occupancy = Column(Float, nullable=False)
    icu_occupancy = Column(Float, nullable=False)
    doctor_workload = Column(Float, nullable=False)
    staff_workload = Column(Float, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    def to_dict(self):
        return {
            "date": self.date,
            "department": self.department,
            "admissions": self.admissions,
            "emergency_cases": self.emergency_cases,
            "bed_occupancy": self.bed_occupancy,
            "icu_occupancy": self.icu_occupancy,
            "doctor_workload": self.doctor_workload,
            "staff_workload": self.staff_workload,
        }


class HistoricalEvent(Base):
    __tablename__ = "historical_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    date = Column(String(50), nullable=False)
    department = Column(String(100), default="Emergency", nullable=False)
    situation = Column(Text, nullable=False)
    admissions = Column(Float, nullable=False)
    emergency_cases = Column(Float, nullable=False)
    bed_occupancy = Column(Float, nullable=False)
    icu_occupancy = Column(Float, nullable=False)
    doctor_workload = Column(Float, nullable=False)
    staff_workload = Column(Float, nullable=False)
    previous_action = Column(Text, nullable=False)
    outcome = Column(Text, nullable=False)
    outcome_status = Column(String(50), default="resolved")

    def to_dict(self):
        return {
            "date": self.date,
            "department": self.department,
            "situation": self.situation,
            "features": {
                "admissions": self.admissions,
                "emergency_cases": self.emergency_cases,
                "bed_occupancy": self.bed_occupancy,
                "icu_occupancy": self.icu_occupancy,
                "doctor_workload": self.doctor_workload,
                "staff_workload": self.staff_workload,
            },
            "previous_action": self.previous_action,
            "outcome": self.outcome,
            "outcome_status": self.outcome_status,
        }


class DecisionRecord(Base):
    __tablename__ = "decision_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now)
    department = Column(String(100), default="Emergency")
    issue = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    administrator_action = Column(Text, nullable=False)
    outcome = Column(String(50), default="pending")
    outcome_details = Column(Text, nullable=True)
    recorded_by = Column(String(100), default="Administrator")

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else "",
            "department": self.department,
            "issue": self.issue,
            "recommendation": self.recommendation,
            "administrator_action": self.administrator_action,
            "outcome": self.outcome,
            "outcome_details": self.outcome_details or "",
            "recorded_by": self.recorded_by,
        }


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="Administrator")
    full_name = Column(String(100), default="Operations Director")

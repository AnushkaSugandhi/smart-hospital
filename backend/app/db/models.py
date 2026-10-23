from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(150), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="Administrator")
    full_name = Column(String(100), default="Operations Director")
    created_at = Column(DateTime, default=utc_now)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "full_name": self.full_name,
        }


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    total_beds = Column(Integer, default=120)
    total_icu = Column(Integer, default=20)
    total_doctors = Column(Integer, default=25)
    total_staff = Column(Integer, default=40)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "total_beds": self.total_beds,
            "total_icu": self.total_icu,
            "total_doctors": self.total_doctors,
            "total_staff": self.total_staff,
        }


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(20), nullable=False)
    department = Column(String(100), default="Emergency")
    triage_priority = Column(String(30), default="Level 2 - High")
    admission_date = Column(String(50), nullable=False)
    status = Column(String(50), default="Admitted")  # Admitted, Discharged, Transferred
    bed_assigned = Column(String(50), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "department": self.department,
            "triage_priority": self.triage_priority,
            "admission_date": self.admission_date,
            "status": self.status,
            "bed_assigned": self.bed_assigned,
        }


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    doctor_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    specialty = Column(String(100), nullable=False)
    department = Column(String(100), default="Emergency")
    shift_status = Column(String(50), default="On-Duty")  # On-Duty, Off-Duty, On-Call
    active_patients = Column(Integer, default=8)
    workload_score = Column(Float, default=10.5)

    def to_dict(self):
        return {
            "id": self.id,
            "doctor_id": self.doctor_id,
            "name": self.name,
            "specialty": self.specialty,
            "department": self.department,
            "shift_status": self.shift_status,
            "active_patients": self.active_patients,
            "workload_score": self.workload_score,
        }


class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    staff_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(100), default="Senior Registered Nurse")
    department = Column(String(100), default="Emergency")
    shift = Column(String(50), default="Morning")
    workload_score = Column(Float, default=8.2)

    def to_dict(self):
        return {
            "id": self.id,
            "staff_id": self.staff_id,
            "name": self.name,
            "role": self.role,
            "department": self.department,
            "shift": self.shift,
            "workload_score": self.workload_score,
        }


class Bed(Base):
    __tablename__ = "beds"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    bed_number = Column(String(50), unique=True, index=True, nullable=False)
    department = Column(String(100), default="Emergency")
    bed_type = Column(String(50), default="Regular")  # Regular, ICU, Step-Down
    is_occupied = Column(Boolean, default=True)
    patient_id = Column(String(50), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "bed_number": self.bed_number,
            "department": self.department,
            "bed_type": self.bed_type,
            "is_occupied": self.is_occupied,
            "patient_id": self.patient_id,
        }


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


class ForecastRecord(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    generated_date = Column(String(50), nullable=False)
    metric = Column(String(50), nullable=False)
    horizon_days = Column(Integer, default=7)
    forecasted_values = Column(Text, nullable=False)  # JSON or comma-separated
    method = Column(String(100), default="Autoregressive Moving Trend")
    quality_score = Column(String(50), default="High (MAPE < 6%)")
    created_at = Column(DateTime, default=utc_now)

    def to_dict(self):
        return {
            "id": self.id,
            "generated_date": self.generated_date,
            "metric": self.metric,
            "horizon_days": self.horizon_days,
            "forecasted_values": self.forecasted_values,
            "method": self.method,
            "quality_score": self.quality_score,
        }


class AlertRecord(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    alert_code = Column(String(50), nullable=False)
    department = Column(String(100), default="Emergency")
    severity = Column(String(30), nullable=False)  # critical, warning, info
    resource_type = Column(String(50), nullable=False)
    reason = Column(Text, nullable=False)
    suggested_action = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    def to_dict(self):
        return {
            "id": self.alert_code,
            "severity": self.severity,
            "resource_type": self.resource_type,
            "reason": self.reason,
            "suggested_action": self.suggested_action,
            "is_active": self.is_active,
        }


class RecommendationRecord(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now)
    department = Column(String(100), default="Emergency")
    trigger_condition = Column(String(200), nullable=False)
    recommendation_text = Column(Text, nullable=False)
    rationale = Column(Text, nullable=False)
    status = Column(String(50), default="Active")

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else "",
            "department": self.department,
            "trigger_condition": self.trigger_condition,
            "recommendation_text": self.recommendation_text,
            "rationale": self.rationale,
            "status": self.status,
        }


class DecisionRecord(Base):
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now)
    department = Column(String(100), default="Emergency")
    issue = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    administrator_action = Column(Text, nullable=False)
    outcome = Column(String(50), default="pending")
    outcome_details = Column(Text, nullable=True)
    recorded_by = Column(String(100), default="Administrator")

    # Relationship to outcomes
    outcomes = relationship("DecisionOutcome", back_populates="decision")

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


class DecisionOutcome(Base):
    __tablename__ = "decision_outcomes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    decision_id = Column(Integer, ForeignKey("decisions.id"), nullable=False)
    evaluated_at = Column(DateTime, default=utc_now)
    bed_occupancy_delta = Column(Float, default=-0.08)
    icu_occupancy_delta = Column(Float, default=-0.05)
    risk_score_delta = Column(Float, default=-14.2)
    evaluation_summary = Column(Text, nullable=False)
    status = Column(String(50), default="stabilized")

    decision = relationship("DecisionRecord", back_populates="outcomes")

    def to_dict(self):
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "evaluated_at": self.evaluated_at.strftime("%Y-%m-%d %H:%M:%S") if self.evaluated_at else "",
            "bed_occupancy_delta": self.bed_occupancy_delta,
            "icu_occupancy_delta": self.icu_occupancy_delta,
            "risk_score_delta": self.risk_score_delta,
            "evaluation_summary": self.evaluation_summary,
            "status": self.status,
        }

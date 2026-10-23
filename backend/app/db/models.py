import json
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


# Optional resource columns (nullable so older CSVs and rows remain valid).
OPTIONAL_RESOURCE_COLUMNS = [
    "ventilators_total", "ventilators_in_use",
    "ot_total", "ot_in_use",
    "nurses_on_duty", "nurses_required",
    "oxygen_stock_hours",
    "blood_a_pos", "blood_a_neg", "blood_b_pos", "blood_b_neg",
    "blood_o_pos", "blood_o_neg", "blood_ab_pos", "blood_ab_neg",
]


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
    ventilators_total = Column(Float, nullable=True)
    ventilators_in_use = Column(Float, nullable=True)
    ot_total = Column(Float, nullable=True)
    ot_in_use = Column(Float, nullable=True)
    nurses_on_duty = Column(Float, nullable=True)
    nurses_required = Column(Float, nullable=True)
    oxygen_stock_hours = Column(Float, nullable=True)
    blood_a_pos = Column(Float, nullable=True)
    blood_a_neg = Column(Float, nullable=True)
    blood_b_pos = Column(Float, nullable=True)
    blood_b_neg = Column(Float, nullable=True)
    blood_o_pos = Column(Float, nullable=True)
    blood_o_neg = Column(Float, nullable=True)
    blood_ab_pos = Column(Float, nullable=True)
    blood_ab_neg = Column(Float, nullable=True)
    # Upload provenance: rows from a batch can be rolled back; a row replaced by
    # a later upload is kept (superseded) so rollback can restore it.
    batch_id = Column(Integer, nullable=True, index=True)
    superseded_by_batch = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now)

    def to_dict(self):
        data = {
            "date": self.date,
            "department": self.department,
            "admissions": self.admissions,
            "emergency_cases": self.emergency_cases,
            "bed_occupancy": self.bed_occupancy,
            "icu_occupancy": self.icu_occupancy,
            "doctor_workload": self.doctor_workload,
            "staff_workload": self.staff_workload,
            "batch_id": self.batch_id,
        }
        for col in OPTIONAL_RESOURCE_COLUMNS:
            data[col] = getattr(self, col)
        return data


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


class UploadBatch(Base):
    __tablename__ = "upload_batches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    uploaded_by = Column(String(100), nullable=False)
    uploaded_at = Column(DateTime, default=utc_now)
    row_count = Column(Integer, default=0)
    status = Column(String(30), default="committed")  # committed, rolled_back
    date_min = Column(String(50), nullable=True)
    date_max = Column(String(50), nullable=True)
    departments = Column(Text, nullable=True)
    dropped_columns = Column(Text, nullable=True)  # personal fields removed on upload
    rolled_back_by = Column(String(100), nullable=True)
    rolled_back_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "uploaded_by": self.uploaded_by,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "row_count": self.row_count,
            "status": self.status,
            "date_min": self.date_min,
            "date_max": self.date_max,
            "departments": [d for d in (self.departments or "").split(",") if d],
            "dropped_columns": [d for d in (self.dropped_columns or "").split(",") if d],
            "rolled_back_by": self.rolled_back_by,
            "rolled_back_at": self.rolled_back_at.isoformat() if self.rolled_back_at else None,
        }


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, index=True)
    username = Column(String(100), index=True, nullable=False)
    role = Column(String(50), nullable=True)
    action = Column(String(60), index=True, nullable=False)
    entity_type = Column(String(60), nullable=True)
    entity_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "username": self.username,
            "role": self.role,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "details": self.details or "",
            "ip_address": self.ip_address,
        }


class AlertState(Base):
    """Persisted state for computed items: alert acknowledge/snooze and
    recommendation approve/dismiss, keyed by the item's stable id."""
    __tablename__ = "alert_state"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    item_id = Column(String(120), unique=True, index=True, nullable=False)
    status = Column(String(30), nullable=False)  # acknowledged, snoozed, approved, dismissed
    snoozed_until = Column(DateTime, nullable=True)
    updated_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    note = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "item_id": self.item_id,
            "status": self.status,
            "snoozed_until": self.snoozed_until.isoformat() if self.snoozed_until else None,
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "note": self.note or "",
        }


class RagChunk(Base):
    """A retrievable piece of anonymised hospital knowledge for the chatbot."""
    __tablename__ = "rag_chunks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    chunk_key = Column(String(200), unique=True, index=True, nullable=False)
    doc_type = Column(String(40), index=True, nullable=False)  # snapshot_week, decision, alert, audit, policy, event
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    department = Column(String(100), nullable=True, index=True)
    date_start = Column(String(20), nullable=True)
    date_end = Column(String(20), nullable=True)
    batch_ids = Column(Text, nullable=True)  # ",3,7," style list for LIKE matching
    min_role = Column(String(20), default="Viewer")
    content_hash = Column(String(64), nullable=False)
    embedding = Column(Text, nullable=True)  # JSON list (portable); pgvector column added when available
    embedding_model = Column(String(80), nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    def to_source(self):
        return {
            "id": self.chunk_key,
            "type": self.doc_type,
            "title": self.title,
            "department": self.department,
            "date_start": self.date_start,
            "date_end": self.date_end,
        }


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(40), primary_key=True)
    username = Column(String(100), index=True, nullable=False)
    title = Column(String(200), default="New chat")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(40), ForeignKey("chat_sessions.id"), index=True, nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    extras = Column(Text, nullable=True)  # JSON: sources, charts, actions, confidence
    feedback = Column(String(10), nullable=True)  # up, down
    created_at = Column(DateTime, default=utc_now)

    def to_dict(self):
        extras = json.loads(self.extras) if self.extras else {}
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "feedback": self.feedback,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            **extras,
        }

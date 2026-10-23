import csv
import io
import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import AuditLog

logger = logging.getLogger("smart_hospital.audit")


def record(
    db: Session,
    user,
    action: str,
    entity_type: str | None = None,
    entity_id=None,
    details=None,
    username: str | None = None,
) -> None:
    """Append an audit entry. Never raises: auditing must not break the request."""
    try:
        if isinstance(details, (dict, list)):
            details = json.dumps(details, default=str)
        db.add(AuditLog(
            username=username or (user.username if user else "anonymous"),
            role=user.role if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details,
            ip_address=getattr(user, "ip_address", None),
        ))
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Audit write failed for %s: %s", action, exc)


def _parse_date(value: str | None, end: bool = False):
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if end and len(value) <= 10:
        parsed = parsed.replace(hour=23, minute=59, second=59)
    return parsed


def query(
    db: Session,
    username: str | None = None,
    action: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
    limit: int = 200,
    offset: int = 0,
):
    q = db.query(AuditLog)
    if username:
        q = q.filter(AuditLog.username == username)
    if action:
        q = q.filter(AuditLog.action == action)
    if (start := _parse_date(date_from)):
        q = q.filter(AuditLog.timestamp >= start)
    if (end := _parse_date(date_to, end=True)):
        q = q.filter(AuditLog.timestamp <= end)
    if search:
        like = f"%{search}%"
        q = q.filter(AuditLog.details.ilike(like) | AuditLog.entity_id.ilike(like) | AuditLog.action.ilike(like))
    total = q.count()
    rows = q.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).offset(offset).limit(limit).all()
    return total, rows


def to_csv(rows) -> str:
    buffer = io.StringIO()
    fields = ["id", "timestamp", "username", "role", "action", "entity_type", "entity_id", "details", "ip_address"]
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: _safe_cell(v) for k, v in row.to_dict().items()})
    return buffer.getvalue()


def _safe_cell(value):
    # Prevent spreadsheet formula injection when the export is opened in Excel.
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value

"""Uploads (profile, commit, batches, rollback) and the audit log."""
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, admin, analyst, viewer
from app.db.database import get_db
from app.db.models import UploadBatch
from app.services import audit_service, data_events
from app.services.upload_service import (
    MAX_UPLOAD_BYTES,
    batch_rows,
    clean_and_commit_data,
    read_uploaded_file,
    rollback_batch,
    schema_info,
    template_csv,
    validate_and_profile,
)

router = APIRouter(prefix="/api/v1", tags=["data"])


async def _read_limited(file: UploadFile) -> bytes:
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(f"File is larger than the {MAX_UPLOAD_BYTES // 1024 // 1024} MB limit.")
    return content


@router.get("/uploads/schema")
def upload_schema(user: CurrentUser = Depends(viewer)):
    return schema_info()


@router.get("/uploads/template")
def upload_template(user: CurrentUser = Depends(viewer)):
    return PlainTextResponse(
        template_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="sh-dss-upload-template.csv"'},
    )


@router.post("/uploads/profile")
async def profile_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(analyst),
):
    """Upload and profile CSV or Excel operational data (nothing is stored)."""
    try:
        content = await _read_limited(file)
        dataframe = read_uploaded_file(file.filename or "", content)
        report = validate_and_profile(dataframe)
        audit_service.record(db, user, "upload_validate", "file", file.filename, {
            "rows": report["total_records"],
            "valid": report["valid_records_after_basic_cleaning"],
            "dropped_personal_columns": report["privacy"]["dropped_columns"],
        })
        return {"filename": file.filename, "report": report}
    except Exception as error:
        return {"filename": file.filename, "error": str(error)}


@router.post("/uploads/commit")
async def commit_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(analyst),
):
    """Validate, clean, and commit uploaded records into the database as a batch."""
    try:
        content = await _read_limited(file)
        dataframe = read_uploaded_file(file.filename or "", content)
        result = clean_and_commit_data(dataframe, db, username=user.username, filename=file.filename or "upload")
    except Exception as error:
        db.rollback()
        return {"status": "error", "filename": file.filename, "error": str(error)}

    audit_service.record(db, user, "upload_commit", "upload_batch", result["batch_id"], {
        "filename": file.filename, "rows": result["saved_count"], "replaced": result["replaced_count"],
        "dates": f"{result['date_min']}..{result['date_max']}",
    })
    data_events.data_changed(db, reason="commit", batch_id=result["batch_id"])
    return {
        "status": "success",
        "filename": file.filename,
        "message": f"Successfully imported {result['saved_count']} records into hospital database.",
        **result,
    }


@router.get("/uploads/batches")
def list_batches(db: Session = Depends(get_db), user: CurrentUser = Depends(viewer)):
    batches = db.query(UploadBatch).order_by(UploadBatch.uploaded_at.desc(), UploadBatch.id.desc()).all()
    return [b.to_dict() for b in batches]


@router.get("/uploads/batches/{batch_id}")
def get_batch(batch_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(analyst)):
    batch = db.query(UploadBatch).filter(UploadBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Upload batch not found.")
    return {"batch": batch.to_dict(), "rows": batch_rows(db, batch_id)}


@router.post("/uploads/batches/{batch_id}/rollback")
def rollback(batch_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(admin)):
    try:
        result = rollback_batch(db, batch_id, user.username)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(409, str(e))
    audit_service.record(db, user, "upload_rollback", "upload_batch", batch_id, {
        "removed_rows": result["removed_rows"], "restored_rows": result["restored_rows"],
    })
    data_events.data_changed(db, reason="rollback", batch_id=batch_id)
    return {"status": "rolled_back", **result}


# ---- Audit log ---------------------------------------------------------------
@router.get("/audit")
def audit_log(
    username: Optional[str] = None,
    action: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(admin),
):
    try:
        total, rows = audit_service.query(db, username, action, date_from, date_to, q, min(limit, 500), offset)
    except ValueError:
        raise HTTPException(400, "Dates must be in YYYY-MM-DD format.")
    return {"total": total, "items": [r.to_dict() for r in rows]}


@router.get("/audit/export")
def audit_export(
    username: Optional[str] = None,
    action: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(admin),
):
    try:
        _, rows = audit_service.query(db, username, action, date_from, date_to, q, limit=50_000)
    except ValueError:
        raise HTTPException(400, "Dates must be in YYYY-MM-DD format.")
    audit_service.record(db, user, "audit_export", "audit_log", None, {"rows": len(rows)})
    return Response(
        audit_service.to_csv(rows),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="audit-log.csv"'},
    )


@router.get("/audit/meta")
def audit_meta(db: Session = Depends(get_db), user: CurrentUser = Depends(admin)):
    from app.db.models import AuditLog
    actions = [r[0] for r in db.query(AuditLog.action).distinct().all()]
    users = [r[0] for r in db.query(AuditLog.username).distinct().all()]
    return {"actions": sorted(actions), "users": sorted(users)}

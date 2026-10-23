import re
from datetime import datetime, timezone
from io import BytesIO, StringIO

import pandas as pd

from app.db.models import OPTIONAL_RESOURCE_COLUMNS, ResourceSnapshot, UploadBatch

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_ROWS = 20_000
ACCEPTED_EXTENSIONS = [".csv", ".xlsx"]
MAX_REPORTED_ERRORS = 200

REQUIRED_COLUMNS = [
    "date",
    "department",
    "admissions",
    "emergency_cases",
    "bed_occupancy",
    "icu_occupancy",
    "doctor_workload",
    "staff_workload",
]

_BLOOD_DESC = {g: f"Units of {g.replace('blood_', '').replace('_pos', '+').replace('_neg', '-').upper()} blood in stock"
               for g in OPTIONAL_RESOURCE_COLUMNS if g.startswith("blood_")}

COLUMN_SCHEMA = [
    {"name": "date", "type": "date", "required": True, "description": "Snapshot date, e.g. 2026-10-23", "example": "2026-10-23"},
    {"name": "department", "type": "text", "required": True, "description": "Department name", "example": "Emergency"},
    {"name": "admissions", "type": "number", "required": True, "description": "Admissions that day", "example": 74},
    {"name": "emergency_cases", "type": "number", "required": True, "description": "Active emergency cases", "example": 16},
    {"name": "bed_occupancy", "type": "ratio", "required": True, "description": "Share of beds occupied, 0-1 (0-100 also accepted)", "example": 0.82},
    {"name": "icu_occupancy", "type": "ratio", "required": True, "description": "Share of ICU beds occupied, 0-1 (0-100 also accepted)", "example": 0.78},
    {"name": "doctor_workload", "type": "number", "required": True, "description": "Patients per doctor", "example": 10.9},
    {"name": "staff_workload", "type": "number", "required": True, "description": "Patients per staff member", "example": 8.4},
    {"name": "ventilators_total", "type": "integer", "required": False, "description": "Ventilators available in total", "example": 24},
    {"name": "ventilators_in_use", "type": "integer", "required": False, "description": "Ventilators currently in use", "example": 15},
    {"name": "ot_total", "type": "integer", "required": False, "description": "Operation theatres in total", "example": 8},
    {"name": "ot_in_use", "type": "integer", "required": False, "description": "Operation theatres in use", "example": 5},
    {"name": "nurses_on_duty", "type": "integer", "required": False, "description": "Nurses on duty", "example": 58},
    {"name": "nurses_required", "type": "integer", "required": False, "description": "Nurses required for current census", "example": 62},
    {"name": "oxygen_stock_hours", "type": "number", "required": False, "description": "Hours of oxygen supply remaining", "example": 40},
] + [
    {"name": col, "type": "integer", "required": False, "description": _BLOOD_DESC[col], "example": 20}
    for col in OPTIONAL_RESOURCE_COLUMNS if col.startswith("blood_")
]
SCHEMA_BY_NAME = {c["name"]: c for c in COLUMN_SCHEMA}
NUMERIC_COLUMNS = [c["name"] for c in COLUMN_SCHEMA if c["type"] in ("number", "integer", "ratio")]
RATIO_COLUMNS = [c["name"] for c in COLUMN_SCHEMA if c["type"] == "ratio"]
CAPACITY_PAIRS = [("ventilators_in_use", "ventilators_total"), ("ot_in_use", "ot_total")]

# ---- Privacy -----------------------------------------------------------------
_PII_NAME = re.compile(
    r"(^|_)(name|first_?name|last_?name|full_?name|patient|phone|mobile|contact|email|e_?mail|"
    r"aadhaa?r|ssn|pan|passport|mrn|uhid|address|dob|birth|guardian|next_of_kin|id)($|_)"
)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE = re.compile(r"\+?\d[\d\s().-]{8,}\d")
_GOV_ID = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")


def _looks_personal(series: pd.Series) -> bool:
    sample = series.dropna().astype(str).head(50)
    if sample.empty:
        return False
    hits = sample.apply(lambda v: bool(_EMAIL.search(v) or _PHONE.fullmatch(v.strip()) or _GOV_ID.search(v)))
    return hits.mean() >= 0.5


def mask_value(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value)
    if (m := _EMAIL.fullmatch(text.strip())):
        local, _, domain = text.partition("@")
        return f"{local[:1]}***@{domain}"
    digits = re.sub(r"\D", "", text)
    if len(digits) >= 8 and len(digits) >= len(text.replace(" ", "")) * 0.6:
        return "•" * (len(digits) - 2) + digits[-2:]
    return (text[:1] + "***") if text else ""


def scrub_text(text: str) -> str:
    """Remove emails/phones/ID numbers embedded in free text fields."""
    text = _EMAIL.sub("[email removed]", text)
    text = _GOV_ID.sub("[id removed]", text)
    return _PHONE.sub("[phone removed]", text)


# ---- Reading -----------------------------------------------------------------
def read_uploaded_file(filename: str, content: bytes) -> pd.DataFrame:
    filename = (filename or "").lower()
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(f"File is {len(content) / 1024 / 1024:.1f} MB; the limit is {MAX_UPLOAD_BYTES // 1024 // 1024} MB.")
    if not content:
        raise ValueError("The file is empty.")

    if filename.endswith(".csv"):
        df = pd.read_csv(BytesIO(content))
    elif filename.endswith(".xlsx"):
        df = pd.read_excel(BytesIO(content))
    else:
        raise ValueError("Only CSV and XLSX files are supported.")

    if len(df) > MAX_ROWS:
        raise ValueError(f"File has {len(df)} rows; the limit is {MAX_ROWS}.")
    df.columns = [re.sub(r"\s+", "_", str(c).strip().lower()) for c in df.columns]
    return df


# ---- Validation --------------------------------------------------------------
def _prepare(df: pd.DataFrame) -> dict:
    original = df.copy()
    known = [c for c in df.columns if c in SCHEMA_BY_NAME]
    unknown = [c for c in df.columns if c not in SCHEMA_BY_NAME]
    pii_columns = [c for c in unknown if _PII_NAME.search(c) or _looks_personal(df[c])]
    ignored_columns = [c for c in unknown if c not in pii_columns]
    missing_columns = [c for c in REQUIRED_COLUMNS if c not in df.columns]

    work = df[known].copy()
    conversions, errors = [], []
    masked_values = 0

    if "department" in work.columns:
        dept = work["department"].astype("string").str.strip()
        scrubbed = dept.fillna("").map(scrub_text)
        masked_values += int((scrubbed != dept.fillna("")).sum())
        work["department"] = scrubbed.where(dept.notna(), None)

    if "date" in work.columns:
        work["date"] = pd.to_datetime(work["date"], errors="coerce")

    for col in [c for c in NUMERIC_COLUMNS if c in work.columns]:
        raw = work[col]
        work[col] = pd.to_numeric(raw, errors="coerce")
        bad = raw.notna() & work[col].isna()
        for idx in work.index[bad]:
            errors.append({"row": int(idx) + 2, "column": col, "value": str(raw[idx]), "error": "Not a number"})

    for col in [c for c in RATIO_COLUMNS if c in work.columns]:
        # Treat the column as 0-100 only when most values are clearly percentages,
        # so a single typo (e.g. 1.5) does not rescale every other row.
        values = work[col].dropna()
        if len(values) and values.max() <= 100 and (values > 1).mean() >= 0.8:
            work[col] = work[col] / 100
            conversions.append(f"{col} looked like a percentage (0-100) and was converted to a 0-1 ratio.")

    # Row-level checks.
    flagged = {(e["row"], e["column"]) for e in errors}
    for idx, row in work.iterrows():
        rownum = int(idx) + 2  # header is row 1 in a spreadsheet
        for col in REQUIRED_COLUMNS:
            if col in work.columns and (pd.isna(row[col]) or (col == "department" and not str(row[col]).strip())):
                if (rownum, col) not in flagged:
                    error = "Invalid date" if col == "date" and pd.notna(original.at[idx, col]) else "Missing required value"
                    errors.append({"row": rownum, "column": col, "value": str(original.at[idx, col]) if col in original else "", "error": error})
        for col in [c for c in NUMERIC_COLUMNS if c in work.columns]:
            value = row[col]
            if pd.isna(value):
                continue
            if value < 0:
                errors.append({"row": rownum, "column": col, "value": str(value), "error": "Must not be negative"})
            elif col in RATIO_COLUMNS and value > 1:
                errors.append({"row": rownum, "column": col, "value": str(value), "error": "Must be between 0 and 1 (or 0-100%)"})
        for used, total in CAPACITY_PAIRS:
            if used in work.columns and total in work.columns and pd.notna(row[used]) and pd.notna(row[total]) and row[used] > row[total]:
                errors.append({"row": rownum, "column": used, "value": str(row[used]), "error": f"Greater than {total} ({row[total]:g})"})

    error_rows = {e["row"] - 2 for e in errors}
    exact_dupes = work.duplicated()
    duplicate_count = int(exact_dupes.sum())
    valid = work[~work.index.isin(error_rows) & ~exact_dupes].copy()

    key_dupes = 0
    if {"date", "department"} <= set(valid.columns):
        key_mask = valid.duplicated(subset=["date", "department"], keep="last")
        key_dupes = int(key_mask.sum())
        valid = valid[~key_mask]
        if key_dupes:
            conversions.append(f"{key_dupes} rows repeated a date + department; the last one was kept.")

    missing_by_column = {c: int(v) for c, v in original[known].isna().sum().items() if v}

    return {
        "original": original,
        "valid": valid,
        "errors": sorted(errors, key=lambda e: (e["row"], e["column"])),
        "error_rows": error_rows,
        "duplicate_count": duplicate_count,
        "key_duplicates": key_dupes,
        "missing_columns": missing_columns,
        "missing_by_column": missing_by_column,
        "pii_columns": pii_columns,
        "ignored_columns": ignored_columns,
        "known": known,
        "conversions": conversions,
        "masked_values": masked_values,
    }


def _jsonable(df: pd.DataFrame) -> list[dict]:
    out = df.copy()
    if "date" in out.columns and pd.api.types.is_datetime64_any_dtype(out["date"]):
        out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    out = out.astype(object).where(out.notna(), None)
    return out.to_dict(orient="records")


def validate_and_profile(df: pd.DataFrame) -> dict:
    p = _prepare(df)
    original = p["original"]

    raw_preview = original.head(10).copy()
    for col in p["pii_columns"]:
        raw_preview[col] = raw_preview[col].map(mask_value)
    raw_rows = _jsonable(raw_preview)
    for i, row in enumerate(raw_rows):
        row["_row"] = i + 2
        row["_errors"] = [e["error"] + f" ({e['column']})" for e in p["errors"] if e["row"] == i + 2]

    invalid_dates = sum(1 for e in p["errors"] if e["column"] == "date")
    valid_count = len(p["valid"]) if not p["missing_columns"] else 0

    return {
        "total_records": len(original),
        "duplicate_records": p["duplicate_count"],
        "duplicate_keys": p["key_duplicates"],
        "missing_values": int(sum(p["missing_by_column"].values())),
        "missing_by_column": p["missing_by_column"],
        "invalid_dates": invalid_dates,
        "invalid_rows": len(p["error_rows"]),
        "row_errors": p["errors"][:MAX_REPORTED_ERRORS],
        "row_errors_truncated": len(p["errors"]) > MAX_REPORTED_ERRORS,
        "valid_records_after_basic_cleaning": valid_count,
        "missing_columns": p["missing_columns"],
        "columns_received": list(original.columns),
        "optional_columns_present": [c for c in p["known"] if c not in REQUIRED_COLUMNS],
        "ignored_columns": p["ignored_columns"],
        "privacy": {
            "dropped_columns": p["pii_columns"],
            "masked_values": p["masked_values"],
            "note": "Personal fields are masked in this preview and are never stored.",
        },
        "conversions": p["conversions"],
        "raw_preview": raw_rows,
        "cleaned_preview": _jsonable(p["valid"].head(10)),
        "can_commit": not p["missing_columns"] and valid_count > 0,
        "message": (
            "This is a data-quality report only. "
            "Click 'Save Records to Database' to commit these records."
        ),
    }


# ---- Commit / rollback -------------------------------------------------------
def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def clean_and_commit_data(df: pd.DataFrame, db, username: str = "system", filename: str = "upload.csv") -> dict:
    """Commit valid rows as a new batch. Rows that replace an existing
    (date, department) mark the old row superseded so rollback can restore it."""
    p = _prepare(df)
    if p["missing_columns"]:
        raise ValueError(f"Missing required columns: {', '.join(p['missing_columns'])}")
    cleaned = p["valid"]
    if cleaned.empty:
        raise ValueError("No valid rows to commit. Fix the row errors shown in the preview and try again.")

    batch = UploadBatch(
        filename=filename[:255],
        uploaded_by=username,
        row_count=0,
        status="committed",
        dropped_columns=",".join(p["pii_columns"]),
    )
    db.add(batch)
    db.flush()

    present_optional = [c for c in OPTIONAL_RESOURCE_COLUMNS if c in cleaned.columns]
    saved_count, replaced_count = 0, 0
    for _, row in cleaned.iterrows():
        date_str = row["date"].strftime("%Y-%m-%d")
        dept = str(row["department"]).strip()

        existing = db.query(ResourceSnapshot).filter(
            ResourceSnapshot.date == date_str,
            ResourceSnapshot.department == dept,
            ResourceSnapshot.superseded_by_batch.is_(None),
        ).all()
        for old in existing:
            old.superseded_by_batch = batch.id
            replaced_count += 1

        values = {col: float(row[col]) for col in REQUIRED_COLUMNS[2:]}
        for col in present_optional:
            values[col] = None if pd.isna(row[col]) else float(row[col])
        db.add(ResourceSnapshot(date=date_str, department=dept, batch_id=batch.id, **values))
        saved_count += 1

    departments = sorted({str(d).strip() for d in cleaned["department"]})
    batch.row_count = saved_count
    batch.date_min = cleaned["date"].min().strftime("%Y-%m-%d")
    batch.date_max = cleaned["date"].max().strftime("%Y-%m-%d")
    batch.departments = ",".join(departments)
    db.commit()

    return {
        "saved_count": saved_count,
        "replaced_count": replaced_count,
        "skipped_rows": len(p["error_rows"]) + p["duplicate_count"] + p["key_duplicates"],
        "batch_id": batch.id,
        "department": departments[0] if len(departments) == 1 else "Multiple",
        "departments": departments,
        "dropped_columns": p["pii_columns"],
        "date_min": batch.date_min,
        "date_max": batch.date_max,
    }


def rollback_batch(db, batch_id: int, username: str) -> dict:
    batch = db.query(UploadBatch).filter(UploadBatch.id == batch_id).first()
    if not batch:
        raise LookupError("Upload batch not found.")
    if batch.status == "rolled_back":
        raise ValueError("This upload has already been rolled back.")

    rows = db.query(ResourceSnapshot).filter(ResourceSnapshot.batch_id == batch_id).all()
    restored = 0
    for row in rows:
        # Rows this batch replaced become active again, unless this batch's row
        # was itself replaced later — then they pass to that later batch.
        previous = db.query(ResourceSnapshot).filter(
            ResourceSnapshot.superseded_by_batch == batch_id,
            ResourceSnapshot.date == row.date,
            ResourceSnapshot.department == row.department,
        ).all()
        for prev in previous:
            prev.superseded_by_batch = row.superseded_by_batch
            restored += 1 if row.superseded_by_batch is None else 0
        db.delete(row)

    batch.status = "rolled_back"
    batch.rolled_back_by = username
    batch.rolled_back_at = _now()
    db.commit()
    return {"batch_id": batch_id, "removed_rows": len(rows), "restored_rows": restored, "batch": batch.to_dict()}


def batch_rows(db, batch_id: int, limit: int = 50) -> list[dict]:
    rows = (db.query(ResourceSnapshot).filter(ResourceSnapshot.batch_id == batch_id)
            .order_by(ResourceSnapshot.date.asc()).limit(limit).all())
    return [r.to_dict() for r in rows]


def template_csv() -> str:
    columns = [c["name"] for c in COLUMN_SCHEMA]
    example = pd.DataFrame([
        {c["name"]: c["example"] for c in COLUMN_SCHEMA},
        {**{c["name"]: c["example"] for c in COLUMN_SCHEMA}, "date": "2026-10-24", "admissions": 78, "bed_occupancy": 0.85},
    ], columns=columns)
    buffer = StringIO()
    example.to_csv(buffer, index=False)
    return buffer.getvalue()


def schema_info() -> dict:
    return {
        "columns": COLUMN_SCHEMA,
        "required": REQUIRED_COLUMNS,
        "optional": [c["name"] for c in COLUMN_SCHEMA if not c["required"]],
        "accepted_formats": ACCEPTED_EXTENSIONS,
        "max_size_mb": MAX_UPLOAD_BYTES // 1024 // 1024,
        "max_rows": MAX_ROWS,
        "privacy": "Columns that look personal (names, phone numbers, emails, IDs) are masked in previews and never stored.",
    }

from io import BytesIO
import pandas as pd
from app.db.models import ResourceSnapshot


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


def read_uploaded_file(filename: str, content: bytes) -> pd.DataFrame:
    filename = filename.lower()

    if filename.endswith(".csv"):
        return pd.read_csv(BytesIO(content))

    if filename.endswith(".xlsx"):
        return pd.read_excel(BytesIO(content))

    raise ValueError("Only CSV and XLSX files are supported.")


def validate_and_profile(df: pd.DataFrame) -> dict:
    original_count = len(df)

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    duplicate_count = int(df.duplicated().sum())
    missing_value_count = int(df.isna().sum().sum())

    invalid_date_count = 0

    cleaned = df.copy()

    if "date" in cleaned.columns:
        cleaned["date"] = pd.to_datetime(
            cleaned["date"],
            errors="coerce",
        )

        invalid_date_count = int(cleaned["date"].isna().sum())

    cleaned = cleaned.drop_duplicates()
    cleaned = cleaned.dropna(subset=["date"])

    preview = cleaned.head(10).copy()

    if "date" in preview.columns:
        preview["date"] = preview["date"].dt.strftime("%Y-%m-%d")

    preview = preview.fillna("").to_dict(orient="records")

    return {
        "total_records": original_count,
        "duplicate_records": duplicate_count,
        "missing_values": missing_value_count,
        "invalid_dates": invalid_date_count,
        "valid_records_after_basic_cleaning": len(cleaned),
        "missing_columns": missing_columns,
        "columns_received": list(df.columns),
        "cleaned_preview": preview,
        "message": (
            "This is a data-quality report only. "
            "Click 'Save Records to Database' to commit these records."
        ),
    }


def clean_and_commit_data(df: pd.DataFrame, db) -> dict:
    """Clean the dataframe and commit valid rows to the resource_snapshots database table."""
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    cleaned = df.copy()
    cleaned["date"] = pd.to_datetime(cleaned["date"], errors="coerce")
    cleaned = cleaned.dropna(subset=["date"]).drop_duplicates()

    saved_count = 0
    for _, row in cleaned.iterrows():
        date_str = row["date"].strftime("%Y-%m-%d")
        dept = str(row.get("department", "Emergency"))

        # Check if record for this date and dept already exists, update or insert
        existing = db.query(ResourceSnapshot).filter(
            ResourceSnapshot.date == date_str,
            ResourceSnapshot.department == dept,
        ).first()

        if existing:
            existing.admissions = float(row["admissions"])
            existing.emergency_cases = float(row["emergency_cases"])
            existing.bed_occupancy = float(row["bed_occupancy"])
            existing.icu_occupancy = float(row["icu_occupancy"])
            existing.doctor_workload = float(row["doctor_workload"])
            existing.staff_workload = float(row["staff_workload"])
        else:
            new_snap = ResourceSnapshot(
                date=date_str,
                department=dept,
                admissions=float(row["admissions"]),
                emergency_cases=float(row["emergency_cases"]),
                bed_occupancy=float(row["bed_occupancy"]),
                icu_occupancy=float(row["icu_occupancy"]),
                doctor_workload=float(row["doctor_workload"]),
                staff_workload=float(row["staff_workload"]),
            )
            db.add(new_snap)
        saved_count += 1

    db.commit()

    return {
        "saved_count": saved_count,
        "department": "Emergency",
        "date_min": cleaned["date"].min().strftime("%Y-%m-%d"),
        "date_max": cleaned["date"].max().strftime("%Y-%m-%d"),
    }
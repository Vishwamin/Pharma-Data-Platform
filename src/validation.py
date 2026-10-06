import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
from sqlalchemy import text

# Ensure project root is in Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.config import Config
from src.logger import get_logger
from src.database import engine, Base
from src.models_bronze import BronzeClinicalTrials
from src.models_quarantine import QuarantineClinicalTrials

logger = get_logger("DataValidationEngine")

# Standard Categorical Mapping Dictionaries
GENDER_MAP = {
    "M": "Male", "MALE": "Male", "m": "Male", "male": "Male",
    "F": "Female", "FEMALE": "Female", "f": "Female", "female": "Female",
    "Male": "Male", "Female": "Female"
}

COUNTRY_MAP = {
    "US": "USA", "UNITED STATES": "USA", "united states": "USA", "usa": "USA",
    "GERMANY": "Germany", "germany": "Germany",
    "JAPAN": "Japan", "japan": "Japan",
    "UK": "UK", "USA": "USA", "Germany": "Germany", "Japan": "Japan", "Canada": "Canada", "France": "France"
}

def validate_and_clean_record(row: dict) -> tuple[bool, dict, list]:
    """
    Applies Data Quality Rules to a single raw record.
    Returns: (is_valid, cleaned_row, violation_reasons)
    """
    violations = []
    cleaned = row.copy()

    # Rule 1: Mandatory Fields Null Check
    mandatory_fields = ["patient_id", "trial_id", "drug_id", "treatment", "outcome", "start_date"]
    for field in mandatory_fields:
        val = row.get(field)
        if val is None or pd.isna(val) or str(val).strip().upper() in ["NONE", "NULL", "N/A", ""]:
            violations.append(f"Missing mandatory field '{field}'")

    # Rule 2: Age Range & Type Validation (18 to 100)
    raw_age = row.get("age")
    if raw_age is None or pd.isna(raw_age) or str(raw_age).strip() == "":
        violations.append("Missing age")
    else:
        try:
            age_int = int(float(raw_age))
            if age_int < 18 or age_int > 100:
                violations.append(f"Invalid age out of bounds (18-100): {age_int}")
            else:
                cleaned["age"] = age_int
        except Exception:
            violations.append(f"Malformed non-numeric age value: '{raw_age}'")

    # Rule 3: Dosage Bounds & Type Validation (0 < dosage <= 500 mg)
    raw_dosage = row.get("dosage")
    if raw_dosage is None or pd.isna(raw_dosage) or str(raw_dosage).strip() == "":
        violations.append("Missing dosage")
    else:
        try:
            dosage_val = float(raw_dosage)
            if dosage_val <= 0 or dosage_val > 500:
                violations.append(f"Dosage out of acceptable range (0-500mg): {dosage_val}")
            else:
                cleaned["dosage"] = dosage_val
        except Exception:
            violations.append(f"Malformed non-numeric dosage value: '{raw_dosage}'")

    # Rule 4: Date Format & Chronological Sanity Check
    start_str = row.get("start_date")
    end_str = row.get("end_date")
    start_dt, end_dt = None, None

    if start_str and not pd.isna(start_str):
        try:
            start_dt = datetime.strptime(str(start_str).strip(), "%Y-%m-%d")
            cleaned["start_date"] = start_dt.strftime("%Y-%m-%d")
        except ValueError:
            violations.append(f"Invalid start_date format (expected YYYY-MM-DD): '{start_str}'")

    if end_str and not pd.isna(end_str):
        try:
            end_dt = datetime.strptime(str(end_str).strip(), "%Y-%m-%d")
            cleaned["end_date"] = end_dt.strftime("%Y-%m-%d")
        except ValueError:
            violations.append(f"Invalid end_date format (expected YYYY-MM-DD): '{end_str}'")

    if start_dt and end_dt and end_dt < start_dt:
        violations.append(f"Chronological Violation: end_date ({end_str}) is before start_date ({start_str})")

    # Rule 5: Categorical Standardization
    raw_gender = str(row.get("gender", "")).strip() if row.get("gender") else ""
    if raw_gender in GENDER_MAP:
        cleaned["gender"] = GENDER_MAP[raw_gender]
    elif raw_gender != "":
        violations.append(f"Unrecognized gender value: '{raw_gender}'")

    raw_country = str(row.get("country", "")).strip() if row.get("country") else ""
    if raw_country in COUNTRY_MAP:
        cleaned["country"] = COUNTRY_MAP[raw_country]
    elif raw_country != "":
        violations.append(f"Unrecognized country value: '{raw_country}'")

    is_valid = len(violations) == 0
    return is_valid, cleaned, violations

def run_data_validation_pipeline() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Phase 3 Engine:
    1. Reads Bronze raw data.
    2. Runs Data Quality Rules Engine.
    3. Quarantines invalid records into database.
    4. Deduplicates valid records.
    5. Returns (df_clean, df_quarantine, metrics).
    """
    logger.info("--- Starting Phase 3: Data Quality Rules & Validation Pipeline ---")

    # Ensure Quarantine tables exist in database
    Base.metadata.create_all(bind=engine)

    # 1. Fetch raw records from Bronze Database Layer
    query = f"SELECT * FROM {BronzeClinicalTrials.__tablename__}"
    df_bronze = pd.read_sql(query, con=engine)

    logger.info(f"Loaded {len(df_bronze)} records from Bronze Database for validation.")

    clean_list = []
    quarantine_list = []

    for _, row in df_bronze.iterrows():
        row_dict = row.to_dict()
        is_valid, cleaned_row, violations = validate_and_clean_record(row_dict)

        if is_valid:
            clean_list.append(cleaned_row)
        else:
            row_dict["violation_reasons"] = "; ".join(violations)
            quarantine_list.append(row_dict)

    df_clean_raw = pd.DataFrame(clean_list)
    df_quarantine = pd.DataFrame(quarantine_list)

    # Deduplication Step on Clean Records
    # Business key for uniqueness: patient_id + trial_id
    if not df_clean_raw.empty:
        initial_clean_count = len(df_clean_raw)
        df_clean = df_clean_raw.drop_duplicates(subset=["patient_id", "trial_id"], keep="first").copy()
        dedup_removed = initial_clean_count - len(df_clean)
        logger.info(f"Deduplication completed: Removed {dedup_removed} duplicate patient trial records.")
    else:
        df_clean = df_clean_raw
        dedup_removed = 0

    # Save Quarantined Bad Records to Database
    if not df_quarantine.empty:
        quarantine_to_save = df_quarantine[[
            "raw_id", "patient_id", "trial_id", "drug_id", "age", "gender",
            "country", "treatment", "dosage", "start_date", "end_date", "outcome", "violation_reasons"
        ]].copy()

        # Truncate existing quarantine table for clean idempotency
        with engine.connect() as conn:
            conn.execute(text(f"DELETE FROM {QuarantineClinicalTrials.__tablename__}"))
            conn.commit()

        quarantine_to_save.to_sql(
            name=QuarantineClinicalTrials.__tablename__,
            con=engine,
            if_exists="append",
            index=False,
            chunksize=500
        )
        logger.info(f"Saved {len(df_quarantine)} invalid records into '{QuarantineClinicalTrials.__tablename__}' database table.")

    # Calculate Data Quality Metrics
    total_records = len(df_bronze)
    valid_count = len(df_clean)
    quarantine_count = len(df_quarantine)
    pass_rate = (valid_count / total_records * 100) if total_records > 0 else 0.0

    metrics = {
        "total_bronze_records": total_records,
        "valid_clean_records": valid_count,
        "quarantined_records": quarantine_count,
        "duplicates_removed": dedup_removed,
        "data_quality_pass_rate_pct": round(pass_rate, 2)
    }

    logger.info("=== Data Quality Validation Metrics ===")
    for key, value in metrics.items():
        logger.info(f"  - {key}: {value}")

    return df_clean, df_quarantine, metrics

if __name__ == "__main__":
    df_valid, df_quarantine, metrics = run_data_validation_pipeline()
    print("\n--- Phase 3 Complete ---")
    print(f"Clean Valid Records: {len(df_valid)}")
    print(f"Quarantined Records: {len(df_quarantine)}")
    if not df_quarantine.empty:
        print("\n--- Sample Quarantined Bad Records & Violation Reasons ---")
        print(df_quarantine[["patient_id", "age", "dosage", "violation_reasons"]].head())

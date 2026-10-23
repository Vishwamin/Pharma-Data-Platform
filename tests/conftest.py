"""
Phase 6: Test Suite — Shared Fixtures & Configuration
=====================================================
conftest.py is pytest's special configuration file.
Fixtures defined here are automatically available to all test files
without needing explicit imports — pytest discovers them automatically.

Fixtures used across the test suite:
  - sample_valid_record    : A perfectly clean clinical trial record dict
  - sample_invalid_records : A list of intentionally bad records
  - sample_silver_df       : A small Silver-like DataFrame for Gold layer tests
"""

import sys
from pathlib import Path
import pandas as pd
import pytest

# Ensure project root is on Python path so imports work from any working directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# SHARED TEST FIXTURES
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_valid_record() -> dict:
    """
    A perfectly clean clinical trial record that should pass ALL validation rules.
    Used by: test_validation.py
    """
    return {
        "patient_id":  "P9001",
        "trial_id":    "CT-101",
        "drug_id":     "DRUG-1",
        "age":         "35",
        "gender":      "Male",
        "country":     "USA",
        "treatment":   "Drug_A_10mg",
        "dosage":      "100.0",
        "start_date":  "2023-01-15",
        "end_date":    "2023-05-20",
        "outcome":     "Completed",
    }


@pytest.fixture
def sample_invalid_records() -> list[dict]:
    """
    A collection of records with specific known violations.
    Each record is paired with a description so tests are self-documenting.
    Used by: test_validation.py
    """
    base = {
        "patient_id": "P9001",
        "trial_id":   "CT-101",
        "drug_id":    "DRUG-1",
        "age":        "35",
        "gender":     "Male",
        "country":    "USA",
        "treatment":  "Drug_A_10mg",
        "dosage":     "100.0",
        "start_date": "2023-01-15",
        "end_date":   "2023-05-20",
        "outcome":    "Completed",
    }

    def mutate(**kwargs) -> dict:
        """Helper: copy base record and apply overrides."""
        r = base.copy()
        r.update(kwargs)
        return r

    return [
        # (record_dict, description_string)
        (mutate(age="-5"),              "age below lower bound"),
        (mutate(age="190"),             "age above upper bound"),
        (mutate(age="ninety"),          "malformed non-numeric age"),
        (mutate(dosage="-50"),          "negative dosage"),
        (mutate(dosage="99999"),        "dosage massively over limit"),
        (mutate(dosage="INVALID"),      "non-numeric dosage string"),
        (mutate(patient_id=None),       "null mandatory field: patient_id"),
        (mutate(outcome=None),          "null mandatory field: outcome"),
        (mutate(treatment=None),        "null mandatory field: treatment"),
        (mutate(start_date="2023-05-20", end_date="2023-01-15"), "end_date before start_date"),
        (mutate(start_date="not-a-date"), "malformed start_date format"),
    ]


@pytest.fixture
def sample_silver_df() -> pd.DataFrame:
    """
    A small Silver-like DataFrame (6 rows) that mimics what spark_silver.py produces.
    Used by: test_build_gold.py
    Pattern: 3 unique patients, 2 unique trials, 2 unique drugs.
    """
    return pd.DataFrame({
        "patient_id":             ["P1001", "P1002", "P1003", "P1004", "P1005", "P1006"],
        "trial_id":               ["CT-101", "CT-101", "CT-102", "CT-102", "CT-101", "CT-102"],
        "drug_id":                ["DRUG-1", "DRUG-2", "DRUG-1", "DRUG-2", "DRUG-1", "DRUG-2"],
        "age":                    [34, 52, 29, 61, 45, 38],
        "gender":                 ["Male", "Female", "Male", "Female", "Male", "Female"],
        "country":                ["USA", "Germany", "Japan", "UK", "USA", "Germany"],
        "treatment":              ["Drug_A_10mg", "Placebo", "Drug_A_10mg", "Placebo", "Drug_B_50mg", "Drug_A_10mg"],
        "dosage":                 [100.0, 50.0, 100.0, 50.0, 100.0, 50.0],
        "start_date":             ["2023-01-01", "2023-02-01", "2023-01-01", "2023-03-01", "2023-01-15", "2023-02-15"],
        "end_date":               ["2023-04-01", "2023-06-01", "2023-05-01", "2023-07-01", "2023-04-15", "2023-06-15"],
        "outcome":                ["Completed", "Withdrawn", "Effective", "Adverse Event", "Completed", "Non-Responsive"],
        "treatment_duration_days":[89, 119, 120, 122, 89, 120],
    })


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Session-level fixture: ensures that all tables (including Gold Star Schema
    and PipelineRun metadata store) exist in the target database.
    If running against SQLite fallback and tables are empty, seeds minimal
    records so API and analytical tests pass offline.
    """
    from src.database import engine, Base
    from src.models_bronze import BronzeClinicalTrials
    from src.models_quarantine import QuarantineClinicalTrials
    from src.models_silver import SilverClinicalTrials
    from src.models_gold import DimPatient, DimTrial, DimDrug, FactClinicalOutcomes
    from src.models_pipeline_run import PipelineRun
    from sqlalchemy import text

    # Ensure all tables exist
    Base.metadata.create_all(bind=engine)

    # Check if fact_clinical_outcomes has data; if empty, seed minimal data
    with engine.connect() as conn:
        try:
            count = conn.execute(text("SELECT COUNT(*) FROM fact_clinical_outcomes")).scalar()
        except Exception:
            count = 0

    if "sqlite" in str(engine.url):
        # Seed minimal dimensions for SQLite fallback if not present
        with engine.connect() as conn:
            conn.execute(text("INSERT OR IGNORE INTO dim_patient (patient_key, patient_id, age, gender, country) VALUES (1, 'P1001', 35, 'Male', 'USA')"))
            conn.execute(text("INSERT OR IGNORE INTO dim_trial (trial_key, trial_id, treatment, start_date, end_date, treatment_duration_days) VALUES (1, 'CT-101', 'Drug_A_10mg', '2023-01-01', '2023-04-01', 90)"))
            conn.execute(text("INSERT OR IGNORE INTO dim_drug (drug_key, drug_id, drug_name) VALUES (1, 'DRUG-1', 'Investigational Drug Alpha')"))
            conn.execute(text("INSERT OR IGNORE INTO dim_drug (drug_key, drug_id, drug_name) VALUES (2, 'DRUG-2', 'Investigational Drug Beta')"))
            conn.execute(text("INSERT OR IGNORE INTO dim_drug (drug_key, drug_id, drug_name) VALUES (3, 'DRUG-3', 'Investigational Drug Gamma')"))
            conn.execute(text("INSERT OR IGNORE INTO dim_drug (drug_key, drug_id, drug_name) VALUES (4, 'DRUG-4', 'Investigational Drug Delta')"))
            conn.execute(text(
                "INSERT OR IGNORE INTO fact_clinical_outcomes "
                "(fact_id, patient_key, trial_key, drug_key, patient_id, trial_id, drug_id, dosage, treatment_duration_days, outcome, outcome_binary, outcome_category) "
                "VALUES (1, 1, 1, 1, 'P1001', 'CT-101', 'DRUG-1', 100.0, 90, 'Completed', 1, 'Positive')"
            ))
            conn.execute(text(
                "INSERT OR IGNORE INTO pipeline_runs "
                "(run_id, run_name, status, triggered_by, duration_seconds) "
                "VALUES (1, 'test_initial_run', 'SUCCESS', 'test', 5.0)"
            ))
            conn.commit()

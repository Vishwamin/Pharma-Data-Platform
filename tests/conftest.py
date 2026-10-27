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
    If the active database is empty (e.g. fresh PostgreSQL service container
    in CI/CD, or clean local SQLite database), seeds minimal records using
    SQLAlchemy ORM so API serving and analytical tests pass out-of-the-box.
    """
    from datetime import date
    from sqlalchemy import text
    from sqlalchemy.orm import Session
    from src.database import engine, Base
    from src.models_bronze import BronzeClinicalTrials
    from src.models_quarantine import QuarantineClinicalTrials
    from src.models_silver import SilverClinicalTrials
    from src.models_gold import DimPatient, DimTrial, DimDrug, FactClinicalOutcomes
    from src.models_pipeline_run import PipelineRun

    # Ensure all tables exist in target database
    Base.metadata.create_all(bind=engine)

    # Check if fact_clinical_outcomes has data
    with engine.connect() as conn:
        try:
            count = conn.execute(text("SELECT COUNT(*) FROM fact_clinical_outcomes")).scalar()
        except Exception:
            count = 0

    if count == 0:
        # Seed test records using ORM (works across PostgreSQL and SQLite)
        with Session(engine) as session:
            # Seed patient dimension
            p = session.query(DimPatient).filter_by(patient_id="P1001").first()
            if not p:
                p = DimPatient(patient_key=1, patient_id="P1001", age=35, gender="Male", country="USA")
                session.add(p)

            # Seed trial dimension
            t = session.query(DimTrial).filter_by(trial_id="CT-101").first()
            if not t:
                t = DimTrial(
                    trial_key=1,
                    trial_id="CT-101",
                    treatment="Drug_A_10mg",
                    start_date=date(2023, 1, 1),
                    end_date=date(2023, 4, 1),
                    treatment_duration_days=90,
                )
                session.add(t)

            # Seed drug dimension (all 4 drugs)
            drugs_to_seed = [
                (1, "DRUG-1", "Investigational Drug Alpha"),
                (2, "DRUG-2", "Investigational Drug Beta"),
                (3, "DRUG-3", "Investigational Drug Gamma"),
                (4, "DRUG-4", "Investigational Drug Delta"),
            ]
            for d_key, d_id, d_name in drugs_to_seed:
                d = session.query(DimDrug).filter_by(drug_id=d_id).first()
                if not d:
                    session.add(DimDrug(drug_key=d_key, drug_id=d_id, drug_name=d_name))

            session.flush()

            # Seed fact table
            fact = session.query(FactClinicalOutcomes).filter_by(fact_id=1).first()
            if not fact:
                session.add(FactClinicalOutcomes(
                    fact_id=1,
                    patient_key=p.patient_key,
                    trial_key=t.trial_key,
                    drug_key=1,
                    patient_id="P1001",
                    trial_id="CT-101",
                    drug_id="DRUG-1",
                    dosage=100.0,
                    treatment_duration_days=90,
                    outcome="Completed",
                    outcome_binary=1,
                    outcome_category="Positive",
                ))

            # Seed pipeline run
            run = session.query(PipelineRun).filter_by(run_id=1).first()
            if not run:
                session.add(PipelineRun(
                    run_id=1,
                    run_name="test_initial_run",
                    status="SUCCESS",
                    triggered_by="test",
                    duration_seconds=5.0,
                ))

            session.commit()

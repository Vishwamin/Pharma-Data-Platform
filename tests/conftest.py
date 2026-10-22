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

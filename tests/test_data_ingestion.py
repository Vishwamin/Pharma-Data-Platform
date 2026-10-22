"""
Phase 6 — Test Module 4: Raw Data Ingestion Tests
===================================================
Tests the raw data file that was generated in Phase 1.
These are DATA QUALITY tests on the actual CSV file —
verifying it has the right structure before loading into Bronze.

What we test:
  1. Raw CSV file exists and is non-empty
  2. All required columns are present in the CSV header
  3. The dataset has a reasonable number of records
  4. patient_id values follow the expected format
  5. Intentional anomalies are actually present (confirms generator worked)

Run with:  pytest tests/test_data_ingestion.py -v
"""

import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.config import Config


@pytest.fixture(scope="module")
def raw_df() -> pd.DataFrame:
    """
    Load the raw CSV once for the whole test module (scope='module' = loaded once,
    not re-read for each test — much faster for large files).
    """
    if not Config.RAW_DATA_PATH.exists():
        pytest.skip(
            f"Raw data file not found at {Config.RAW_DATA_PATH}. "
            "Run: python src/generate_synthetic_data.py"
        )
    return pd.read_csv(Config.RAW_DATA_PATH, dtype=str)  # dtype=str = read everything as string (like Bronze)


# ===========================================================================
# 1. FILE-LEVEL CHECKS
# ===========================================================================

class TestRawFileExists:
    """The raw CSV file must exist and be non-trivially sized."""

    def test_raw_data_file_exists(self):
        """Phase 1 must have been run — raw CSV file must exist on disk."""
        assert Config.RAW_DATA_PATH.exists(), (
            f"Raw data file missing. Run: python src/generate_synthetic_data.py"
        )

    def test_raw_data_file_is_not_empty(self):
        """The raw CSV must have content — not a zero-byte file."""
        assert Config.RAW_DATA_PATH.stat().st_size > 0, "Raw data file is empty (0 bytes)"

    def test_raw_data_file_has_csv_extension(self):
        """File must have .csv extension."""
        assert Config.RAW_DATA_PATH.suffix == ".csv"


# ===========================================================================
# 2. SCHEMA CHECKS — COLUMNS
# ===========================================================================

class TestRawDataSchema:
    """The CSV header must contain all required columns."""

    def test_all_required_columns_present(self, raw_df):
        """Every column in REQUIRED_COLUMNS must appear in the CSV header."""
        for col in Config.REQUIRED_COLUMNS:
            assert col in raw_df.columns, (
                f"Required column '{col}' not found in raw CSV. "
                f"Available columns: {list(raw_df.columns)}"
            )

    def test_no_completely_unnamed_columns(self, raw_df):
        """There should be no unnamed/blank column headers."""
        for col in raw_df.columns:
            assert col.strip() != "", f"Found blank column name in CSV header"
            assert not col.startswith("Unnamed:"), f"Found unnamed column: '{col}'"


# ===========================================================================
# 3. ROW COUNT CHECKS
# ===========================================================================

class TestRawDataRowCount:
    """The dataset must have a reasonable number of records."""

    def test_minimum_row_count(self, raw_df):
        """The raw dataset must have at least 100 rows to be meaningful."""
        assert len(raw_df) >= 100, (
            f"Raw dataset too small ({len(raw_df)} rows). Expected at least 100."
        )

    def test_expected_row_count_range(self, raw_df):
        """
        Generator creates 1000 base records + ~3% duplicates = ~1030 rows.
        We allow a wider range to accommodate different run configurations.
        """
        assert 900 <= len(raw_df) <= 1200, (
            f"Row count {len(raw_df)} outside expected range [900, 1200]."
        )


# ===========================================================================
# 4. PATIENT ID FORMAT CHECKS
# ===========================================================================

class TestPatientIdFormat:
    """patient_id values follow the format P#### (e.g., P1001, P1005)."""

    def test_patient_ids_not_null(self, raw_df):
        """Most patient_id values should be non-null (some may be intentionally nulled)."""
        non_null_count = raw_df["patient_id"].notna().sum()
        assert non_null_count > len(raw_df) * 0.8, (
            f"Too many null patient_ids: {raw_df['patient_id'].isna().sum()} out of {len(raw_df)}"
        )

    def test_patient_ids_start_with_P(self, raw_df):
        """Non-null patient IDs should start with 'P'."""
        non_null_ids = raw_df["patient_id"].dropna()
        p_prefix_count = non_null_ids.str.startswith("P").sum()
        assert p_prefix_count > len(non_null_ids) * 0.9, (
            f"Most patient IDs should start with 'P', "
            f"but only {p_prefix_count}/{len(non_null_ids)} do."
        )


# ===========================================================================
# 5. ANOMALY PRESENCE CHECKS
# ===========================================================================

class TestIntentionalAnomaliesPresent:
    """
    The synthetic data generator intentionally injects bad data.
    These tests confirm the anomalies actually made it into the file —
    so we know our validation engine has real bad data to catch.
    """

    def test_null_values_exist_in_dataset(self, raw_df):
        """
        The generator injects ~6% null values across treatment/outcome fields.
        At least one null must be present somewhere in the dataset.
        """
        has_any_null = raw_df.isnull().any().any()
        assert has_any_null, (
            "No null values found in raw data. "
            "The synthetic generator may not have injected anomalies correctly."
        )

    def test_multiple_trial_ids_present(self, raw_df):
        """The generator creates records for CT-101 through CT-105 — at least 3 unique trials."""
        unique_trials = raw_df["trial_id"].nunique()
        assert unique_trials >= 3, (
            f"Expected at least 3 unique trial IDs, got {unique_trials}"
        )

    def test_multiple_countries_present(self, raw_df):
        """Multiple countries should be present in the raw data."""
        non_null_countries = raw_df["country"].dropna()
        unique_countries = non_null_countries.nunique()
        assert unique_countries >= 3, (
            f"Expected at least 3 unique countries, got {unique_countries}"
        )

    def test_multiple_outcome_values_present(self, raw_df):
        """Multiple outcome categories should exist (Completed, Withdrawn, etc.)."""
        non_null_outcomes = raw_df["outcome"].dropna()
        unique_outcomes = non_null_outcomes.nunique()
        assert unique_outcomes >= 2, (
            f"Expected at least 2 unique outcomes, got {unique_outcomes}"
        )

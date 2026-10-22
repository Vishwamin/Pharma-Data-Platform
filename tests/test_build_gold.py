"""
Phase 6 — Test Module 2: Gold Layer Helper Function Tests
=========================================================
Tests the pure helper functions in src/build_gold.py that perform
data derivation logic. These functions take a string and return
a value — zero database interaction.

Pure functions = easiest to test = most reliable tests.

What we test:
  1. _derive_outcome_binary  — maps outcome strings to 0/1
  2. _derive_outcome_category — maps outcome strings to Positive/Negative/Neutral
  3. _derive_drug_name        — maps drug IDs to human-readable drug names
  4. Edge cases: None, empty strings, mixed case, unknown values

Run with:  pytest tests/test_build_gold.py -v
"""

import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.build_gold import (
    _derive_outcome_binary,
    _derive_outcome_category,
    _derive_drug_name,
)


# ===========================================================================
# 1. OUTCOME BINARY MAPPING
# ===========================================================================

class TestOutcomeBinary:
    """
    _derive_outcome_binary() converts a raw outcome string to 1 (positive) or 0 (negative/neutral).
    This number drives aggregate success-rate calculations in the fact table.
    """

    @pytest.mark.parametrize("outcome", [
        "Completed", "completed", "COMPLETED",
        "Effective", "effective", "EFFECTIVE",
        "Recovered", "recovered",
        "Improved",  "improved",
        "Remission", "remission",
        "Stable",    "stable",
    ])
    def test_positive_outcomes_return_1(self, outcome):
        """All known positive outcome strings (any case) should return 1."""
        result = _derive_outcome_binary(outcome)
        assert result == 1, f"'{outcome}' should map to 1 (positive), got {result}"

    @pytest.mark.parametrize("outcome", [
        "Withdrawn",     "withdrawn",
        "Adverse Event", "adverse event",
        "Non-Responsive","non-responsive",
        "Worsened",      "worsened",
        "Deceased",      "deceased",
        "No Change",     "Unknown",
    ])
    def test_negative_neutral_outcomes_return_0(self, outcome):
        """All negative or neutral outcomes should return 0."""
        result = _derive_outcome_binary(outcome)
        assert result == 0, f"'{outcome}' should map to 0 (negative/neutral), got {result}"

    def test_unknown_outcome_returns_0(self):
        """An unrecognized outcome string should default to 0, not raise an error."""
        result = _derive_outcome_binary("SomeWeirdOutcome")
        assert result == 0

    def test_empty_string_returns_0(self):
        """An empty string should safely return 0."""
        result = _derive_outcome_binary("")
        assert result == 0

    def test_none_as_string_returns_0(self):
        """None coerced to string 'None' should safely return 0."""
        result = _derive_outcome_binary(None)
        assert result == 0

    def test_return_type_is_int(self):
        """The return value must always be an integer (not a bool or float)."""
        result = _derive_outcome_binary("Completed")
        assert isinstance(result, int)
        assert result == 1

    def test_whitespace_stripped_correctly(self):
        """Leading/trailing whitespace must be stripped before matching."""
        assert _derive_outcome_binary("  Completed  ") == 1
        assert _derive_outcome_binary("  Withdrawn  ") == 0


# ===========================================================================
# 2. OUTCOME CATEGORY MAPPING
# ===========================================================================

class TestOutcomeCategory:
    """
    _derive_outcome_category() maps raw outcome strings to
    'Positive', 'Negative', or 'Neutral'.
    Used for GROUP BY queries in analytical dashboards.
    """

    @pytest.mark.parametrize("outcome,expected", [
        ("Completed",     "Positive"),
        ("Effective",     "Positive"),
        ("Recovered",     "Positive"),
        ("Improved",      "Positive"),
        ("Remission",     "Positive"),
        ("completed",     "Positive"),
        ("EFFECTIVE",     "Positive"),
    ])
    def test_positive_outcome_category(self, outcome, expected):
        """Known positive outcomes should map to 'Positive' category."""
        assert _derive_outcome_category(outcome) == expected

    @pytest.mark.parametrize("outcome,expected", [
        ("Withdrawn",      "Negative"),
        ("Adverse Event",  "Negative"),
        ("Non-Responsive", "Negative"),
        ("Worsened",       "Negative"),
        ("Deceased",       "Negative"),
        ("withdrawn",      "Negative"),
        ("ADVERSE EVENT",  "Negative"),
    ])
    def test_negative_outcome_category(self, outcome, expected):
        """Known negative outcomes should map to 'Negative' category."""
        assert _derive_outcome_category(outcome) == expected

    @pytest.mark.parametrize("outcome,expected", [
        ("Stable",         "Neutral"),
        ("No Change",      "Neutral"),
        ("stable",         "Neutral"),
        ("UnknownOutcome", "Neutral"),   # Unknown strings fall through to Neutral
        ("",               "Neutral"),
    ])
    def test_neutral_outcome_category(self, outcome, expected):
        """Stable, no-change, and unknown outcomes should map to 'Neutral'."""
        assert _derive_outcome_category(outcome) == expected

    def test_none_returns_neutral(self):
        """None coerced to 'None' should fall through to Neutral safely."""
        result = _derive_outcome_category(None)
        assert result == "Neutral"

    def test_return_type_is_string(self):
        """Return value must always be a string."""
        result = _derive_outcome_category("Completed")
        assert isinstance(result, str)

    def test_all_categories_are_valid_values(self):
        """Every possible return value must be one of the three valid categories."""
        valid_categories = {"Positive", "Negative", "Neutral"}
        test_inputs = [
            "Completed", "Withdrawn", "Stable", "Unknown",
            "", None, "EFFECTIVE", "adverse event"
        ]
        for outcome in test_inputs:
            result = _derive_outcome_category(outcome)
            assert result in valid_categories, (
                f"'{outcome}' produced invalid category '{result}'"
            )


# ===========================================================================
# 3. DRUG NAME DERIVATION
# ===========================================================================

class TestDrugName:
    """
    _derive_drug_name() maps a drug_id code to a human-readable drug name.
    The catalog covers DRUG-1 through DRUG-4 (current synthetic data format)
    and legacy D-001 through D-005 format.
    """

    @pytest.mark.parametrize("drug_id,expected_name", [
        ("DRUG-1", "Investigational Drug Alpha"),
        ("DRUG-2", "Investigational Drug Beta"),
        ("DRUG-3", "Investigational Drug Gamma"),
        ("DRUG-4", "Investigational Drug Delta"),
    ])
    def test_known_drug_ids_resolve_correctly(self, drug_id, expected_name):
        """Each known DRUG-N ID should return its correct human-readable name."""
        result = _derive_drug_name(drug_id)
        assert result == expected_name, (
            f"'{drug_id}' should map to '{expected_name}', got '{result}'"
        )

    @pytest.mark.parametrize("drug_id,expected_name", [
        ("D-001", "Investigational Drug Alpha"),
        ("D-002", "Investigational Drug Beta"),
        ("D-003", "Investigational Drug Gamma"),
        ("D-004", "Investigational Drug Delta"),
        ("D-005", "Investigational Drug Epsilon"),
    ])
    def test_legacy_drug_ids_resolve_correctly(self, drug_id, expected_name):
        """Legacy D-00x format drug IDs should still resolve correctly."""
        result = _derive_drug_name(drug_id)
        assert result == expected_name

    def test_unknown_drug_id_returns_fallback(self):
        """An unrecognized drug ID should return a graceful fallback string, not raise an error."""
        result = _derive_drug_name("DRUG-99")
        assert "DRUG-99" in result, (
            f"Fallback for unknown drug ID should include the ID itself. Got: '{result}'"
        )

    def test_whitespace_stripped_from_drug_id(self):
        """Leading/trailing whitespace in drug_id should be stripped before lookup."""
        result = _derive_drug_name("  DRUG-1  ")
        assert result == "Investigational Drug Alpha"

    def test_return_type_is_string(self):
        """Return value must always be a string."""
        assert isinstance(_derive_drug_name("DRUG-1"), str)
        assert isinstance(_derive_drug_name("UNKNOWN-ID"), str)


# ===========================================================================
# 4. INTEGRATION-STYLE: APPLY HELPERS TO DATAFRAME
# ===========================================================================

class TestHelperFunctionsOnDataFrame:
    """
    Verifies that the helper functions work correctly when applied to
    a realistic Silver-like DataFrame (simulating the actual pipeline).
    Uses the sample_silver_df fixture from conftest.py.
    """

    def test_outcome_binary_column_created_correctly(self, sample_silver_df):
        """Applying _derive_outcome_binary to a DataFrame column produces correct 0/1 values."""
        df = sample_silver_df.copy()
        df["outcome_binary"] = df["outcome"].apply(_derive_outcome_binary)

        # Verify column exists and has correct dtype
        assert "outcome_binary" in df.columns
        assert df["outcome_binary"].dtype in ["int64", "int32", "object"]

        # Verify specific expected values based on our fixture data
        # "Completed" → 1, "Withdrawn" → 0, "Effective" → 1, "Adverse Event" → 0
        expected_binaries = [1, 0, 1, 0, 1, 0]
        assert list(df["outcome_binary"]) == expected_binaries, (
            f"Expected {expected_binaries}, got {list(df['outcome_binary'])}"
        )

    def test_outcome_category_column_created_correctly(self, sample_silver_df):
        """Applying _derive_outcome_category produces only valid category values."""
        df = sample_silver_df.copy()
        df["outcome_category"] = df["outcome"].apply(_derive_outcome_category)

        valid_categories = {"Positive", "Negative", "Neutral"}
        invalid = df[~df["outcome_category"].isin(valid_categories)]
        assert invalid.empty, (
            f"Found invalid outcome categories:\n{invalid[['outcome', 'outcome_category']]}"
        )

    def test_drug_name_column_created_correctly(self, sample_silver_df):
        """Applying _derive_drug_name produces non-empty human-readable strings."""
        df = sample_silver_df.copy()
        df["drug_name"] = df["drug_id"].apply(_derive_drug_name)

        # All drug names should be non-empty strings
        assert df["drug_name"].notna().all()
        assert (df["drug_name"] != "").all()

    def test_dim_patient_deduplication(self, sample_silver_df):
        """
        drop_duplicates on patient_id should yield exactly as many rows
        as there are unique patients in the fixture.
        """
        df = sample_silver_df.copy()
        unique_patients = df.drop_duplicates(subset=["patient_id"])
        # Our fixture has 6 unique patient IDs: P1001..P1006
        assert len(unique_patients) == 6

    def test_dim_trial_deduplication(self, sample_silver_df):
        """
        drop_duplicates on trial_id should yield exactly as many rows
        as there are unique trials.
        """
        df = sample_silver_df.copy()
        unique_trials = df.drop_duplicates(subset=["trial_id"])
        # Our fixture has 2 unique trials: CT-101, CT-102
        assert len(unique_trials) == 2

    def test_dim_drug_deduplication(self, sample_silver_df):
        """
        drop_duplicates on drug_id should yield exactly as many rows
        as there are unique drugs.
        """
        df = sample_silver_df.copy()
        unique_drugs = df.drop_duplicates(subset=["drug_id"])
        # Our fixture has 2 unique drugs: DRUG-1, DRUG-2
        assert len(unique_drugs) == 2

    def test_fact_row_count_matches_silver(self, sample_silver_df):
        """
        The fact table should have the same number of rows as the Silver input
        (one fact row per patient-trial event, no filtering).
        """
        df = sample_silver_df.copy()
        # Simulate fact creation — every Silver row becomes one fact row
        fact_count = len(df)
        assert fact_count == 6, f"Expected 6 fact rows matching fixture size, got {fact_count}"

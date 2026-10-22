"""
Phase 6 — Test Module 1: Data Validation Engine Tests
======================================================
Tests the core business rules inside src/validation.py.

These are UNIT TESTS — they test individual functions in isolation
without touching the database at all. This makes them fast (<1 second)
and reliable (no external dependencies).

What we test:
  1. Valid records pass correctly (no false positives)
  2. Each individual validation rule correctly catches bad data
  3. Categorical standardization (gender, country) works
  4. Output structure (return types and shapes) is always correct
  5. Edge cases (boundary values, whitespace, mixed casing)

Run with:  pytest tests/test_validation.py -v
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.validation import validate_and_clean_record, GENDER_MAP, COUNTRY_MAP


# ===========================================================================
# 1. VALID RECORD — SHOULD ALWAYS PASS
# ===========================================================================

class TestValidRecord:
    """A completely clean record should pass every rule with zero violations."""

    def test_valid_record_is_accepted(self, sample_valid_record):
        """The record should be marked as valid (is_valid = True)."""
        is_valid, _, violations = validate_and_clean_record(sample_valid_record)
        assert is_valid is True, f"Expected valid record to pass but got: {violations}"

    def test_valid_record_has_no_violations(self, sample_valid_record):
        """The violations list should be completely empty for a clean record."""
        _, _, violations = validate_and_clean_record(sample_valid_record)
        assert violations == [], f"Unexpected violations: {violations}"

    def test_valid_record_returns_three_items(self, sample_valid_record):
        """validate_and_clean_record must always return a 3-tuple."""
        result = validate_and_clean_record(sample_valid_record)
        assert len(result) == 3

    def test_valid_record_cleaned_row_is_dict(self, sample_valid_record):
        """The cleaned_row must be a dictionary."""
        _, cleaned, _ = validate_and_clean_record(sample_valid_record)
        assert isinstance(cleaned, dict)

    def test_valid_record_age_converted_to_int(self, sample_valid_record):
        """Age should be cast to integer in the cleaned record."""
        _, cleaned, _ = validate_and_clean_record(sample_valid_record)
        assert isinstance(cleaned["age"], int)
        assert cleaned["age"] == 35

    def test_valid_record_dosage_converted_to_float(self, sample_valid_record):
        """Dosage should be cast to float in the cleaned record."""
        _, cleaned, _ = validate_and_clean_record(sample_valid_record)
        assert isinstance(cleaned["dosage"], float)
        assert cleaned["dosage"] == 100.0


# ===========================================================================
# 2. AGE VALIDATION RULES
# ===========================================================================

class TestAgeValidation:
    """Rule 2: Age must be an integer between 18 and 100 (inclusive)."""

    def test_age_below_minimum_rejected(self, sample_valid_record):
        """Age of 17 is below the 18-year minimum — must be rejected."""
        record = {**sample_valid_record, "age": "17"}
        is_valid, _, violations = validate_and_clean_record(record)
        assert is_valid is False
        assert any("age" in v.lower() for v in violations)

    def test_age_at_minimum_boundary_accepted(self, sample_valid_record):
        """Age of exactly 18 is the minimum valid age — must be accepted."""
        record = {**sample_valid_record, "age": "18"}
        is_valid, _, violations = validate_and_clean_record(record)
        assert is_valid is True, f"Age 18 should pass. Got violations: {violations}"

    def test_age_at_maximum_boundary_accepted(self, sample_valid_record):
        """Age of exactly 100 is the maximum valid age — must be accepted."""
        record = {**sample_valid_record, "age": "100"}
        is_valid, _, violations = validate_and_clean_record(record)
        assert is_valid is True, f"Age 100 should pass. Got violations: {violations}"

    def test_age_above_maximum_rejected(self, sample_valid_record):
        """Age of 101 exceeds the 100-year maximum — must be rejected."""
        record = {**sample_valid_record, "age": "101"}
        is_valid, _, violations = validate_and_clean_record(record)
        assert is_valid is False
        assert any("age" in v.lower() for v in violations)

    def test_negative_age_rejected(self, sample_valid_record):
        """Negative ages are nonsensical and must be rejected."""
        record = {**sample_valid_record, "age": "-5"}
        is_valid, _, _ = validate_and_clean_record(record)
        assert is_valid is False

    def test_very_large_age_rejected(self, sample_valid_record):
        """Age of 190 is impossible — must be rejected."""
        record = {**sample_valid_record, "age": "190"}
        is_valid, _, _ = validate_and_clean_record(record)
        assert is_valid is False

    def test_non_numeric_age_rejected(self, sample_valid_record):
        """String 'ninety' is not parseable as a number — must be rejected."""
        record = {**sample_valid_record, "age": "ninety"}
        is_valid, _, violations = validate_and_clean_record(record)
        assert is_valid is False
        assert any("age" in v.lower() for v in violations)

    def test_float_age_string_accepted(self, sample_valid_record):
        """Age written as '35.0' (float string) should be accepted and cast to int 35."""
        record = {**sample_valid_record, "age": "35.0"}
        is_valid, cleaned, violations = validate_and_clean_record(record)
        assert is_valid is True, f"Float-string age should pass. Violations: {violations}"
        assert cleaned["age"] == 35


# ===========================================================================
# 3. DOSAGE VALIDATION RULES
# ===========================================================================

class TestDosageValidation:
    """Rule 3: Dosage must be a float > 0 and <= 500."""

    def test_valid_dosage_accepted(self, sample_valid_record):
        """Dosage of 100mg is well within range — must pass."""
        is_valid, _, violations = validate_and_clean_record(sample_valid_record)
        assert is_valid is True, f"Violations: {violations}"

    def test_zero_dosage_rejected(self, sample_valid_record):
        """Dosage of exactly 0 is invalid (must be > 0) — must be rejected."""
        record = {**sample_valid_record, "dosage": "0"}
        is_valid, _, _ = validate_and_clean_record(record)
        assert is_valid is False

    def test_negative_dosage_rejected(self, sample_valid_record):
        """Negative dosage is physically impossible — must be rejected."""
        record = {**sample_valid_record, "dosage": "-50"}
        is_valid, _, _ = validate_and_clean_record(record)
        assert is_valid is False

    def test_dosage_at_upper_boundary_accepted(self, sample_valid_record):
        """Dosage of exactly 500mg is the upper limit — must pass."""
        record = {**sample_valid_record, "dosage": "500"}
        is_valid, _, violations = validate_and_clean_record(record)
        assert is_valid is True, f"500mg dosage should pass. Violations: {violations}"

    def test_dosage_above_upper_limit_rejected(self, sample_valid_record):
        """Dosage of 501mg exceeds the 500mg maximum — must be rejected."""
        record = {**sample_valid_record, "dosage": "501"}
        is_valid, _, _ = validate_and_clean_record(record)
        assert is_valid is False

    def test_non_numeric_dosage_rejected(self, sample_valid_record):
        """'INVALID_DOSAGE' string cannot be parsed — must be rejected."""
        record = {**sample_valid_record, "dosage": "INVALID_DOSAGE"}
        is_valid, _, violations = validate_and_clean_record(record)
        assert is_valid is False
        assert any("dosage" in v.lower() for v in violations)

    def test_massive_dosage_rejected(self, sample_valid_record):
        """99999mg is an obviously wrong value — must be rejected."""
        record = {**sample_valid_record, "dosage": "99999"}
        is_valid, _, _ = validate_and_clean_record(record)
        assert is_valid is False


# ===========================================================================
# 4. MANDATORY FIELD NULL CHECKS
# ===========================================================================

class TestMandatoryFieldNullChecks:
    """Rule 1: patient_id, trial_id, drug_id, treatment, outcome, start_date
       must all be present and non-null.
    """

    @pytest.mark.parametrize("field", [
        "patient_id", "trial_id", "drug_id", "treatment", "outcome", "start_date"
    ])
    def test_null_mandatory_field_rejected(self, sample_valid_record, field):
        """
        Parametrized: each mandatory field is individually nulled out
        and the record must be rejected in each case.
        This one test covers all 6 mandatory fields automatically.
        """
        record = {**sample_valid_record, field: None}
        is_valid, _, violations = validate_and_clean_record(record)
        assert is_valid is False, f"Expected rejection when '{field}' is None"
        assert any(field in v for v in violations), (
            f"Expected '{field}' to appear in violations. Got: {violations}"
        )

    @pytest.mark.parametrize("field", ["patient_id", "trial_id"])
    def test_empty_string_mandatory_field_rejected(self, sample_valid_record, field):
        """Empty strings are treated as missing values and must be rejected."""
        record = {**sample_valid_record, field: ""}
        is_valid, _, violations = validate_and_clean_record(record)
        assert is_valid is False, f"Empty '{field}' should fail validation"


# ===========================================================================
# 5. DATE VALIDATION RULES
# ===========================================================================

class TestDateValidation:
    """Rule 4: Dates must be in YYYY-MM-DD format and end_date >= start_date."""

    def test_valid_dates_accepted(self, sample_valid_record):
        """Correct format and valid chronological order — must pass."""
        is_valid, _, violations = validate_and_clean_record(sample_valid_record)
        assert is_valid is True, f"Violations: {violations}"

    def test_end_date_before_start_date_rejected(self, sample_valid_record):
        """When end_date < start_date, chronological order is violated — reject."""
        record = {**sample_valid_record, "start_date": "2023-05-01", "end_date": "2023-01-01"}
        is_valid, _, violations = validate_and_clean_record(record)
        assert is_valid is False
        assert any("chronological" in v.lower() or "end_date" in v.lower() for v in violations)

    def test_same_start_and_end_date_accepted(self, sample_valid_record):
        """Same-day start and end is technically valid (end_date >= start_date)."""
        record = {**sample_valid_record, "start_date": "2023-01-15", "end_date": "2023-01-15"}
        is_valid, _, violations = validate_and_clean_record(record)
        assert is_valid is True, f"Same-day dates should be valid. Violations: {violations}"

    def test_malformed_start_date_rejected(self, sample_valid_record):
        """Date in wrong format (DD/MM/YYYY) cannot be parsed — reject."""
        record = {**sample_valid_record, "start_date": "15-01-2023"}
        is_valid, _, violations = validate_and_clean_record(record)
        assert is_valid is False
        assert any("start_date" in v.lower() for v in violations)


# ===========================================================================
# 6. CATEGORICAL STANDARDIZATION
# ===========================================================================

class TestCategoricalStandardization:
    """Rule 5: Gender and Country values get standardized to canonical forms."""

    @pytest.mark.parametrize("raw_gender, expected", [
        ("M",      "Male"),
        ("m",      "Male"),
        ("MALE",   "Male"),
        ("F",      "Female"),
        ("f",      "Female"),
        ("FEMALE", "Female"),
        ("Male",   "Male"),
        ("Female", "Female"),
    ])
    def test_gender_standardization(self, sample_valid_record, raw_gender, expected):
        """All gender variants should be standardized to 'Male' or 'Female'."""
        record = {**sample_valid_record, "gender": raw_gender}
        _, cleaned, _ = validate_and_clean_record(record)
        assert cleaned["gender"] == expected, (
            f"'{raw_gender}' should map to '{expected}', got '{cleaned.get('gender')}'"
        )

    @pytest.mark.parametrize("raw_country, expected", [
        ("US",            "USA"),
        ("UNITED STATES", "USA"),
        ("usa",           "USA"),
        ("GERMANY",       "Germany"),
        ("germany",       "Germany"),
        ("JAPAN",         "Japan"),
        ("japan",         "Japan"),
        ("USA",           "USA"),
        ("Germany",       "Germany"),
    ])
    def test_country_standardization(self, sample_valid_record, raw_country, expected):
        """All country variants should be standardized to canonical country names."""
        record = {**sample_valid_record, "country": raw_country}
        _, cleaned, _ = validate_and_clean_record(record)
        assert cleaned["country"] == expected, (
            f"'{raw_country}' should map to '{expected}', got '{cleaned.get('country')}'"
        )

    def test_unrecognized_gender_adds_violation(self, sample_valid_record):
        """An unknown gender value like 'X' should add a violation."""
        record = {**sample_valid_record, "gender": "Nonbinary"}
        is_valid, _, violations = validate_and_clean_record(record)
        assert is_valid is False
        assert any("gender" in v.lower() for v in violations)


# ===========================================================================
# 7. BATCH OF INVALID RECORDS (parametrized from conftest.py fixture)
# ===========================================================================

class TestInvalidRecordsBatch:
    """
    Iterates through the full sample_invalid_records fixture from conftest.py
    and asserts that every single one is correctly rejected.
    """

    def test_each_invalid_record_is_rejected(self, sample_invalid_records):
        """
        Every record in the invalid batch must produce is_valid=False.
        If any record unexpectedly passes, the test fails with a clear message.
        """
        for record, description in sample_invalid_records:
            is_valid, _, violations = validate_and_clean_record(record)
            assert is_valid is False, (
                f"Record with '{description}' should be INVALID but passed validation.\n"
                f"  Record: {record}\n"
                f"  Violations: {violations}"
            )

    def test_each_invalid_record_has_violations(self, sample_invalid_records):
        """Every rejected record must have at least one violation message."""
        for record, description in sample_invalid_records:
            _, _, violations = validate_and_clean_record(record)
            assert len(violations) > 0, (
                f"Record with '{description}' should have violations but violations list is empty.\n"
                f"  Record: {record}"
            )

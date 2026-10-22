"""
Phase 6 — Test Module 3: Configuration & Project Structure Tests
================================================================
Tests that project-level configuration is correct and all required
files, directories, and environment settings are in place.

These tests catch common "it works on my machine" bugs — missing
config values, wrong paths, bad environment setup — before they
silently cause failures in production.

What we test:
  1. Config class has all required attributes
  2. Required data paths exist on disk
  3. Required columns list is complete and non-empty
  4. Database URI formats are correctly constructed
  5. Project directory structure is intact

Run with:  pytest tests/test_config.py -v
"""

import sys
import os
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.config import Config, BASE_DIR


# ===========================================================================
# 1. CONFIG CLASS STRUCTURE
# ===========================================================================

class TestConfigAttributes:
    """Config class must expose all required attributes for the pipeline to run."""

    def test_env_attribute_exists(self):
        """Config.ENV must be set (defaults to 'development')."""
        assert hasattr(Config, "ENV")
        assert Config.ENV is not None

    def test_raw_data_path_attribute_exists(self):
        """Config.RAW_DATA_PATH must be defined."""
        assert hasattr(Config, "RAW_DATA_PATH")

    def test_log_file_path_attribute_exists(self):
        """Config.LOG_FILE_PATH must be defined."""
        assert hasattr(Config, "LOG_FILE_PATH")

    def test_postgres_uri_attribute_exists(self):
        """Config.POSTGRES_URI must be defined."""
        assert hasattr(Config, "POSTGRES_URI")

    def test_sqlite_uri_attribute_exists(self):
        """Config.SQLITE_URI fallback must be defined."""
        assert hasattr(Config, "SQLITE_URI")

    def test_required_columns_attribute_exists(self):
        """Config.REQUIRED_COLUMNS must be defined."""
        assert hasattr(Config, "REQUIRED_COLUMNS")


# ===========================================================================
# 2. DATABASE URI FORMAT VALIDATION
# ===========================================================================

class TestDatabaseURIs:
    """Database connection strings must follow the expected format."""

    def test_postgres_uri_starts_with_correct_driver(self):
        """PostgreSQL URI must use the psycopg2 driver prefix."""
        assert Config.POSTGRES_URI.startswith("postgresql+psycopg2://"), (
            f"PostgreSQL URI should start with 'postgresql+psycopg2://'. Got: {Config.POSTGRES_URI[:50]}"
        )

    def test_sqlite_uri_starts_with_correct_prefix(self):
        """SQLite fallback URI must start with 'sqlite:///'."""
        assert Config.SQLITE_URI.startswith("sqlite:///"), (
            f"SQLite URI should start with 'sqlite:///'. Got: {Config.SQLITE_URI[:50]}"
        )

    def test_postgres_uri_contains_database_name(self):
        """PostgreSQL URI must include the database name."""
        assert "pharma_clinical_db" in Config.POSTGRES_URI

    def test_postgres_uri_contains_host(self):
        """PostgreSQL URI must contain a host (default: localhost)."""
        assert "localhost" in Config.POSTGRES_URI or "@" in Config.POSTGRES_URI

    def test_sqlite_uri_points_to_data_directory(self):
        """SQLite URI must point inside the project's data/ directory."""
        assert "data" in Config.SQLITE_URI


# ===========================================================================
# 3. PATH OBJECTS AND TYPES
# ===========================================================================

class TestConfigPaths:
    """Config paths must be Path objects (not plain strings) for cross-platform compatibility."""

    def test_raw_data_path_is_path_object(self):
        """RAW_DATA_PATH must be a pathlib.Path, not a plain string."""
        assert isinstance(Config.RAW_DATA_PATH, Path), (
            f"RAW_DATA_PATH should be a Path object, got {type(Config.RAW_DATA_PATH)}"
        )

    def test_log_file_path_is_path_object(self):
        """LOG_FILE_PATH must be a pathlib.Path, not a plain string."""
        assert isinstance(Config.LOG_FILE_PATH, Path)

    def test_raw_data_path_ends_with_csv(self):
        """The raw data path should point to a CSV file."""
        assert Config.RAW_DATA_PATH.suffix == ".csv", (
            f"Expected .csv extension, got: {Config.RAW_DATA_PATH.suffix}"
        )

    def test_raw_data_parent_directory_exists(self):
        """The directory containing the raw data file must exist."""
        assert Config.RAW_DATA_PATH.parent.exists(), (
            f"Raw data directory does not exist: {Config.RAW_DATA_PATH.parent}"
        )

    def test_log_file_parent_directory_exists(self):
        """The logs/ directory must exist (Config creates it on import)."""
        assert Config.LOG_FILE_PATH.parent.exists(), (
            f"Logs directory does not exist: {Config.LOG_FILE_PATH.parent}"
        )


# ===========================================================================
# 4. REQUIRED COLUMNS LIST
# ===========================================================================

class TestRequiredColumns:
    """REQUIRED_COLUMNS must be complete for the ingestion and validation stages to work."""

    EXPECTED_COLUMNS = [
        "patient_id", "trial_id", "drug_id",
        "age", "gender", "country",
        "treatment", "dosage",
        "start_date", "end_date", "outcome"
    ]

    def test_required_columns_is_a_list(self):
        """REQUIRED_COLUMNS must be a list type."""
        assert isinstance(Config.REQUIRED_COLUMNS, list)

    def test_required_columns_is_not_empty(self):
        """REQUIRED_COLUMNS must not be empty."""
        assert len(Config.REQUIRED_COLUMNS) > 0

    def test_required_columns_contains_all_expected_fields(self):
        """Every expected column name must be present in REQUIRED_COLUMNS."""
        for col in self.EXPECTED_COLUMNS:
            assert col in Config.REQUIRED_COLUMNS, (
                f"Expected column '{col}' missing from REQUIRED_COLUMNS. "
                f"Current list: {Config.REQUIRED_COLUMNS}"
            )

    def test_required_columns_contains_no_duplicates(self):
        """There should be no duplicate column names in REQUIRED_COLUMNS."""
        assert len(Config.REQUIRED_COLUMNS) == len(set(Config.REQUIRED_COLUMNS)), (
            "REQUIRED_COLUMNS contains duplicate entries"
        )


# ===========================================================================
# 5. PROJECT DIRECTORY STRUCTURE
# ===========================================================================

class TestProjectStructure:
    """Critical project directories and source files must exist."""

    @pytest.mark.parametrize("directory", [
        "src",
        "config",
        "data",
        "data/raw",
        "logs",
        "sql",
        "tests",
    ])
    def test_required_directory_exists(self, directory):
        """Each critical project directory must exist on disk."""
        target = BASE_DIR / directory
        assert target.exists() and target.is_dir(), (
            f"Required directory '{directory}' not found at: {target}"
        )

    @pytest.mark.parametrize("src_file", [
        "src/__init__.py",
        "src/logger.py",
        "src/database.py",
        "src/generate_synthetic_data.py",
        "src/load_bronze.py",
        "src/validation.py",
        "src/spark_silver.py",
        "src/build_gold.py",
        "src/models_bronze.py",
        "src/models_quarantine.py",
        "src/models_silver.py",
        "src/models_gold.py",
        "config/config.py",
        "config/__init__.py",
        "requirements.txt",
        "README.md",
    ])
    def test_required_source_file_exists(self, src_file):
        """Each critical source file must exist on disk."""
        target = BASE_DIR / src_file
        assert target.exists() and target.is_file(), (
            f"Required source file '{src_file}' not found at: {target}"
        )

    def test_raw_data_file_exists(self):
        """The raw CSV data file must have been generated (Phase 1 prerequisite)."""
        assert Config.RAW_DATA_PATH.exists(), (
            f"Raw data file not found. Run: python src/generate_synthetic_data.py\n"
            f"Expected at: {Config.RAW_DATA_PATH}"
        )

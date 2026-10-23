"""
Phase 6 — Test Module 5: Orchestrator Unit Tests
=================================================
Tests the Phase 7 orchestrator's logic and metadata model
WITHOUT running the actual pipeline (no DB writes, no file I/O).

What we test:
  1. STAGE_REGISTRY is complete and correctly structured
  2. DEFAULT_STAGES contains all expected stage keys
  3. PipelineRun ORM model has the required columns/attributes
  4. _run_tests() parses pytest output correctly
  5. Stage key validation — unknown stages handled gracefully

Run with:  pytest tests/test_orchestrator.py -v
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.orchestrator import STAGE_REGISTRY, DEFAULT_STAGES
from src.models_pipeline_run import PipelineRun


# ===========================================================================
# 1. STAGE REGISTRY STRUCTURE
# ===========================================================================

class TestStageRegistry:
    """STAGE_REGISTRY must be complete and each entry correctly structured."""

    EXPECTED_STAGES = ["generate", "bronze", "validate", "silver", "gold", "test"]
    REQUIRED_KEYS   = ["label", "description", "module", "callable"]

    def test_all_expected_stages_registered(self):
        """Every phase must have an entry in the registry."""
        for stage in self.EXPECTED_STAGES:
            assert stage in STAGE_REGISTRY, (
                f"Stage '{stage}' missing from STAGE_REGISTRY. "
                f"Current keys: {list(STAGE_REGISTRY.keys())}"
            )

    def test_no_extra_unexpected_stages(self):
        """Registry should not contain unrecognised stage keys."""
        extra = set(STAGE_REGISTRY.keys()) - set(self.EXPECTED_STAGES)
        assert extra == set(), f"Unexpected stage keys in registry: {extra}"

    @pytest.mark.parametrize("stage_key", ["generate", "bronze", "validate", "silver", "gold", "test"])
    def test_each_stage_has_required_fields(self, stage_key):
        """Every stage entry must have label, description, module, callable."""
        entry = STAGE_REGISTRY[stage_key]
        for key in self.REQUIRED_KEYS:
            assert key in entry, (
                f"Stage '{stage_key}' missing required field '{key}'. "
                f"Entry: {entry}"
            )

    @pytest.mark.parametrize("stage_key", ["generate", "bronze", "validate", "silver", "gold", "test"])
    def test_each_stage_label_is_non_empty_string(self, stage_key):
        """Every stage label must be a non-empty string."""
        label = STAGE_REGISTRY[stage_key]["label"]
        assert isinstance(label, str) and len(label) > 0

    @pytest.mark.parametrize("stage_key", ["generate", "bronze", "validate", "silver", "gold", "test"])
    def test_each_stage_callable_starts_with_underscore(self, stage_key):
        """Callable names follow the _run_* naming convention."""
        callable_name = STAGE_REGISTRY[stage_key]["callable"]
        assert callable_name.startswith("_run_"), (
            f"Stage '{stage_key}' callable '{callable_name}' should start with '_run_'"
        )


# ===========================================================================
# 2. DEFAULT STAGES ORDER
# ===========================================================================

class TestDefaultStages:
    """DEFAULT_STAGES must list all 6 stages in the correct execution order."""

    def test_default_stages_is_a_list(self):
        """DEFAULT_STAGES must be a list."""
        assert isinstance(DEFAULT_STAGES, list)

    def test_default_stages_has_correct_length(self):
        """Must contain exactly 6 stages."""
        assert len(DEFAULT_STAGES) == 6, (
            f"Expected 6 stages in DEFAULT_STAGES, got {len(DEFAULT_STAGES)}: {DEFAULT_STAGES}"
        )

    def test_default_stages_starts_with_generate(self):
        """Pipeline must always start with data generation."""
        assert DEFAULT_STAGES[0] == "generate", (
            f"First stage must be 'generate', got '{DEFAULT_STAGES[0]}'"
        )

    def test_default_stages_ends_with_test(self):
        """Tests must run last — after all data has been processed."""
        assert DEFAULT_STAGES[-1] == "test", (
            f"Last stage must be 'test', got '{DEFAULT_STAGES[-1]}'"
        )

    def test_bronze_before_validate(self):
        """Bronze must be loaded BEFORE validation can run."""
        assert DEFAULT_STAGES.index("bronze") < DEFAULT_STAGES.index("validate"), (
            "Stage 'bronze' must come before 'validate' in DEFAULT_STAGES"
        )

    def test_validate_before_silver(self):
        """Validation must run BEFORE Silver transformation."""
        assert DEFAULT_STAGES.index("validate") < DEFAULT_STAGES.index("silver"), (
            "Stage 'validate' must come before 'silver' in DEFAULT_STAGES"
        )

    def test_silver_before_gold(self):
        """Silver layer must exist BEFORE Gold can be built."""
        assert DEFAULT_STAGES.index("silver") < DEFAULT_STAGES.index("gold"), (
            "Stage 'silver' must come before 'gold' in DEFAULT_STAGES"
        )

    def test_no_duplicate_stages(self):
        """No stage should appear twice in DEFAULT_STAGES."""
        assert len(DEFAULT_STAGES) == len(set(DEFAULT_STAGES)), (
            f"Duplicate stage keys in DEFAULT_STAGES: {DEFAULT_STAGES}"
        )

    def test_all_default_stages_exist_in_registry(self):
        """Every stage in DEFAULT_STAGES must be registered in STAGE_REGISTRY."""
        for stage in DEFAULT_STAGES:
            assert stage in STAGE_REGISTRY, (
                f"Stage '{stage}' is in DEFAULT_STAGES but missing from STAGE_REGISTRY"
            )


# ===========================================================================
# 3. PIPELINE RUN ORM MODEL
# ===========================================================================

class TestPipelineRunModel:
    """PipelineRun ORM must have all required columns for metadata tracking."""

    REQUIRED_COLUMNS = [
        "run_id", "run_name", "status", "triggered_by",
        "started_at", "completed_at", "duration_seconds",
        "stages_planned", "stages_completed", "stages_failed",
        "bronze_records", "valid_records", "silver_records",
        "gold_fact_rows", "tests_passed", "tests_failed",
        "error_message",
    ]

    def test_pipeline_run_table_name(self):
        """Table must be named 'pipeline_runs'."""
        assert PipelineRun.__tablename__ == "pipeline_runs"

    @pytest.mark.parametrize("column_name", [
        "run_id", "run_name", "status", "triggered_by",
        "started_at", "completed_at", "duration_seconds",
        "stages_planned", "stages_completed", "stages_failed",
        "bronze_records", "valid_records", "silver_records",
        "gold_fact_rows", "tests_passed", "tests_failed",
        "error_message",
    ])
    def test_required_column_exists_on_model(self, column_name):
        """Each required column must exist as an attribute on PipelineRun."""
        assert hasattr(PipelineRun, column_name), (
            f"PipelineRun model missing required column: '{column_name}'"
        )

    def test_pipeline_run_is_instantiable(self):
        """PipelineRun can be instantiated with basic fields without error."""
        run = PipelineRun(
            run_name     = "test_run",
            status       = "RUNNING",
            triggered_by = "test",
        )
        assert run.run_name     == "test_run"
        assert run.status       == "RUNNING"
        assert run.triggered_by == "test"

    def test_pipeline_run_repr_is_readable(self):
        """__repr__ must return a non-empty string for debugging."""
        run = PipelineRun(run_name="test", status="SUCCESS")
        repr_str = repr(run)
        assert isinstance(repr_str, str)
        assert "PipelineRun" in repr_str
        assert "SUCCESS" in repr_str

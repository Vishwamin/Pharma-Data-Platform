"""
Phase 8 — Test Module 6: Clinical Data Serving API Unit Tests
=============================================================
Direct unit tests for the FastAPI route handlers, Pydantic schemas,
and analytical query logic in src/api_serving.py.

Tests:
  1. System Endpoints:
     - root() returns service metadata and endpoints listing
     - health_check() confirms database connectivity & telemetry
  2. Clinical Analytics Endpoints:
     - get_clinical_kpis() returns valid aggregated KPIs
     - get_drug_efficacy() returns comparative performance per drug
     - get_demographics_summary() returns country & gender breakdowns
     - get_trials_summary() returns clinical trial metrics
  3. Pipeline Telemetry Endpoints:
     - get_pipeline_runs() returns audit trail records
     - trigger_pipeline_run() verifies background task scheduling

Run with:
  pytest tests/test_api_serving.py -v
"""

import sys
from pathlib import Path
from datetime import datetime
import pytest
from fastapi import BackgroundTasks

# Ensure project root is in Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api_serving import (
    root,
    health_check,
    get_clinical_kpis,
    get_drug_efficacy,
    get_demographics_summary,
    get_trials_summary,
    get_pipeline_runs,
    trigger_pipeline_run,
    ClinicalKPIs,
    HealthResponse,
    DemographicsSummary,
    TriggerRunRequest,
    TriggerRunResponse,
)


# ===========================================================================
# 1. SYSTEM ENDPOINTS
# ===========================================================================
class TestSystemEndpoints:
    """Tests for service info and health check route handlers."""

    def test_root_endpoint(self):
        """root() should return service identity and endpoint listing."""
        data = root()
        assert isinstance(data, dict)
        assert "service" in data
        assert "version" in data
        assert "docs_url" in data
        assert isinstance(data["api_endpoints"], list)
        assert len(data["api_endpoints"]) >= 5

    def test_health_check_endpoint(self):
        """health_check() should return HealthResponse with healthy DB status."""
        health = health_check()
        assert isinstance(health, HealthResponse)
        assert health.status == "HEALTHY"
        assert len(health.database) > 0
        assert health.gold_records_count >= 0
        assert isinstance(health.timestamp, datetime)


# ===========================================================================
# 2. CLINICAL ANALYTICS ENDPOINTS
# ===========================================================================
class TestClinicalAnalyticsEndpoints:
    """Tests for core analytical queries against Gold Star Schema."""

    def test_get_clinical_kpis(self):
        """get_clinical_kpis() should return top-level clinical performance metrics."""
        kpis = get_clinical_kpis()
        assert isinstance(kpis, ClinicalKPIs)
        assert kpis.total_fact_records > 0
        assert kpis.unique_patients > 0
        assert kpis.unique_trials > 0
        assert kpis.unique_drugs > 0
        assert 0.0 <= kpis.overall_positive_rate_pct <= 100.0
        assert kpis.avg_treatment_duration_days > 0
        assert kpis.avg_dosage_mg > 0

    def test_get_drug_efficacy(self):
        """get_drug_efficacy() should return comparative performance per drug."""
        items = get_drug_efficacy(min_trials=0)
        assert isinstance(items, list)
        assert len(items) >= 1  # At least one drug analysed

        for item in items:
            assert item.drug_id.startswith("DRUG-")
            assert len(item.drug_name) > 0
            assert item.total_trials > 0
            assert 0.0 <= item.success_rate_pct <= 100.0
            assert item.avg_dosage_mg > 0

    def test_get_drug_efficacy_filter_min_trials(self):
        """get_drug_efficacy() with min_trials filter."""
        items = get_drug_efficacy(min_trials=100)
        assert isinstance(items, list)
        for item in items:
            assert item.total_trials >= 100

    def test_get_demographics_summary(self):
        """get_demographics_summary() should return country and gender cohorts."""
        summary = get_demographics_summary()
        assert isinstance(summary, DemographicsSummary)
        assert len(summary.by_country) > 0
        assert len(summary.by_gender) > 0

        # Validate country demographic item
        first_country = summary.by_country[0]
        assert len(first_country.country) > 0
        assert first_country.patient_count > 0

        # Validate gender demographic item
        first_gender = summary.by_gender[0]
        assert first_gender.gender in ["Male", "Female"]
        assert first_gender.patient_count > 0
        assert first_gender.avg_age > 0

    def test_get_trials_summary(self):
        """get_trials_summary() should return metrics per clinical trial."""
        items = get_trials_summary()
        assert isinstance(items, list)
        assert len(items) >= 1  # At least one trial summary available

        for item in items:
            assert item.trial_id.startswith("CT-")
            assert len(item.treatment) > 0
            assert item.patient_count > 0


# ===========================================================================
# 3. PIPELINE TELEMETRY ENDPOINTS
# ===========================================================================
class TestPipelineTelemetryEndpoints:
    """Tests for pipeline telemetry and webhook trigger endpoints."""

    def test_get_pipeline_runs(self):
        """get_pipeline_runs() should return historical executions from metadata store."""
        items = get_pipeline_runs(limit=5)
        assert isinstance(items, list)
        if len(items) > 0:
            first = items[0]
            assert "run_id" in first
            assert "status" in first
            assert "started_at" in first

    def test_trigger_pipeline_run_endpoint(self, monkeypatch):
        """trigger_pipeline_run() should schedule pipeline run in BackgroundTasks."""
        # Mock run_pipeline to prevent launching full pipeline during quick unit test
        def mock_run_pipeline(*args, **kwargs):
            return None

        monkeypatch.setattr("src.api_serving.run_pipeline", mock_run_pipeline)

        background_tasks = BackgroundTasks()
        payload = TriggerRunRequest(
            run_name="test_api_trigger",
            stages=["gold", "test"],
        )
        response = trigger_pipeline_run(payload=payload, background_tasks=background_tasks)

        assert isinstance(response, TriggerRunResponse)
        assert response.run_name == "test_api_trigger"
        assert "successfully scheduled" in response.message
        assert response.stages_requested == ["gold", "test"]
        assert len(background_tasks.tasks) == 1

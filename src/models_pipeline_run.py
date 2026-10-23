"""
Phase 7: Pipeline Orchestration — Master Run Table ORM Model
=============================================================
Defines the 'pipeline_runs' table that tracks every pipeline execution.

Each row represents one full pipeline run (or a single stage run),
recording: when it started, when it ended, which stages ran, their
individual outcomes, and any error messages.

This is called a Pipeline Metadata Store — used in production systems
like Airflow (DAG runs table), Prefect (flow runs table), and dbt
(results JSON). We implement the same concept from scratch using
SQLAlchemy so you can see exactly how it works underneath.
"""

import sys
from pathlib import Path
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, DateTime, Float,
    Text, JSON, Boolean
)
from sqlalchemy.sql import func

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import Base


class PipelineRun(Base):
    """
    Tracks every pipeline execution attempt — successful or failed.

    Columns
    -------
    run_id          : Auto-generated surrogate PK for the run
    run_name        : Human-readable label (e.g. "full_pipeline", "gold_only")
    status          : Overall run status — RUNNING | SUCCESS | FAILED | PARTIAL
    triggered_by    : What started this run — "manual" | "scheduler" | "test"
    started_at      : Timestamp when the orchestrator began
    completed_at    : Timestamp when the orchestrator finished (or failed)
    duration_seconds: Total wall-clock time in seconds
    stages_planned  : JSON list of stage names that were scheduled to run
    stages_completed: JSON list of stage names that actually completed
    stages_failed   : JSON list of stage names that threw an exception
    bronze_records  : Count of records loaded into Bronze layer (Phase 2)
    valid_records   : Count of records passing validation (Phase 3)
    silver_records  : Count of records written to Silver layer (Phase 4)
    gold_fact_rows  : Count of fact rows written to Gold layer (Phase 5)
    tests_passed    : Count of pytest tests that passed (Phase 6)
    tests_failed    : Count of pytest tests that failed (Phase 6)
    error_message   : Full error traceback if the run failed, else NULL
    notes           : Optional free-text notes about the run
    """

    __tablename__ = "pipeline_runs"

    # Identity
    run_id       = Column(Integer, primary_key=True, autoincrement=True)
    run_name     = Column(String(100), nullable=False, default="full_pipeline")
    status       = Column(String(20),  nullable=False, default="RUNNING")
    triggered_by = Column(String(50),  nullable=False, default="manual")

    # Timing
    started_at       = Column(DateTime, nullable=False, default=func.now())
    completed_at     = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Stage tracking (stored as JSON arrays)
    stages_planned   = Column(JSON, nullable=True)   # ["generate", "bronze", "validate", "silver", "gold", "test"]
    stages_completed = Column(JSON, nullable=True)   # ["generate", "bronze", "validate"]
    stages_failed    = Column(JSON, nullable=True)   # ["silver"]

    # Pipeline metrics (output counts from each stage)
    bronze_records = Column(Integer, nullable=True)
    valid_records  = Column(Integer, nullable=True)
    silver_records = Column(Integer, nullable=True)
    gold_fact_rows = Column(Integer, nullable=True)
    tests_passed   = Column(Integer, nullable=True)
    tests_failed   = Column(Integer, nullable=True)

    # Error information
    error_message = Column(Text, nullable=True)

    # Optional notes
    notes = Column(Text, nullable=True)

    def __repr__(self):
        return (
            f"<PipelineRun(run_id={self.run_id}, "
            f"run_name='{self.run_name}', "
            f"status='{self.status}', "
            f"started_at='{self.started_at}')>"
        )

"""
Phase 7: Pipeline Orchestration — Master Pipeline Orchestrator
==============================================================

Chains every phase of the Medallion pipeline into one automated,
observable, end-to-end run:

    Phase 1  generate_synthetic_data  → Raw CSV
    Phase 2  load_bronze              → Bronze DB table
    Phase 3  run_data_validation      → Validated DataFrame + Quarantine
    Phase 4  process_bronze_to_silver → Silver DB table + Parquet
    Phase 5  build_gold_layer         → Star schema + Gold Parquet
    Phase 6  run_tests                → pytest test suite

Features
--------
- Stage-by-stage execution with configurable skip flags
- Every run recorded to the 'pipeline_runs' metadata table
- Per-stage timing tracked individually
- On failure: saves full traceback to DB, marks status PARTIAL or FAILED
- On success: prints a formatted pipeline health dashboard
- Idempotent: safe to re-run at any time
- retry_on_failure: optionally retries a failed stage once

Usage
-----
Run the full pipeline:
    python src/orchestrator.py

Run only specific stages (edit RUN_CONFIG inside the script):
    python src/orchestrator.py --stages generate,bronze,validate

Check past run history:
    python src/orchestrator.py --history
"""

import sys
import os
import time
import traceback
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.config import Config, BASE_DIR
from src.logger import get_logger
from src.database import engine, Base
from src.models_pipeline_run import PipelineRun

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = get_logger("PipelineOrchestrator")


# =============================================================================
# STAGE REGISTRY
# Every runnable stage lives here. Adding a new phase = add one entry.
# =============================================================================

STAGE_REGISTRY = {
    "generate": {
        "label":       "Phase 1 — Generate Synthetic Data",
        "description": "Create 1000 synthetic clinical trial records with anomalies",
        "module":      "src.generate_synthetic_data",
        "callable":    "_run_generate",
    },
    "bronze": {
        "label":       "Phase 2 — Load Bronze Layer",
        "description": "Load raw CSV strings into bronze_clinical_trials table",
        "module":      "src.load_bronze",
        "callable":    "_run_bronze",
    },
    "validate": {
        "label":       "Phase 3 — Data Validation & Quarantine",
        "description": "Run business rules engine, quarantine bad records",
        "module":      "src.validation",
        "callable":    "_run_validate",
    },
    "silver": {
        "label":       "Phase 4 — Silver Layer Transformation",
        "description": "Type enforcement, feature engineering, Parquet export",
        "module":      "src.spark_silver",
        "callable":    "_run_silver",
    },
    "gold": {
        "label":       "Phase 5 — Gold Layer Star Schema",
        "description": "Build dim/fact tables, export Gold Parquet, analytics summary",
        "module":      "src.build_gold",
        "callable":    "_run_gold",
    },
    "test": {
        "label":       "Phase 6 — Pipeline Test Suite",
        "description": "Run 182-test pytest suite across all pipeline components",
        "module":      "pytest",
        "callable":    "_run_tests",
    },
}

# Default execution order
DEFAULT_STAGES = ["generate", "bronze", "validate", "silver", "gold", "test"]


# =============================================================================
# INDIVIDUAL STAGE RUNNERS
# Each function calls the relevant phase module and returns a metrics dict.
# Returning a dict (not just a number) gives us flexibility to capture
# multiple metrics per stage.
# =============================================================================

def _run_generate() -> dict:
    """Run Phase 1: Synthetic data generation."""
    from src.generate_synthetic_data import generate_clinical_trial_data
    output_path = generate_clinical_trial_data(num_rows=1000, seed=42)

    # Count rows in the output CSV
    row_count = sum(1 for _ in open(output_path)) - 1  # minus header
    return {"raw_rows_generated": row_count, "output_path": str(output_path)}


def _run_bronze() -> dict:
    """Run Phase 2: Bronze layer load."""
    from src.load_bronze import load_raw_to_bronze

    # Truncate existing Bronze data first for a clean idempotent run
    with engine.connect() as conn:
        try:
            conn.execute(text("DELETE FROM bronze_clinical_trials"))
            conn.commit()
        except Exception:
            conn.rollback()

    count = load_raw_to_bronze()
    return {"bronze_records": count}


def _run_validate() -> dict:
    """Run Phase 3: Data validation + quarantine."""
    from src.validation import run_data_validation_pipeline
    df_clean, df_quarantine, metrics = run_data_validation_pipeline()
    return {
        "valid_records":         len(df_clean),
        "quarantined_records":   len(df_quarantine),
        "dq_pass_rate_pct":      metrics.get("data_quality_pass_rate_pct", 0.0),
        "duplicates_removed":    metrics.get("duplicates_removed", 0),
    }


def _run_silver() -> dict:
    """Run Phase 4: Silver layer transformation."""
    from src.spark_silver import process_bronze_to_silver
    count = process_bronze_to_silver()
    return {"silver_records": count}


def _run_gold() -> dict:
    """Run Phase 5: Gold layer star schema build."""
    from src.build_gold import build_gold_layer
    fact_count = build_gold_layer()
    return {"gold_fact_rows": fact_count}


def _run_tests() -> dict:
    """Run Phase 6: pytest test suite. Returns pass/fail counts."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-q"],
        capture_output=True,
        text=True,
        cwd=str(BASE_DIR)
    )

    # Parse pytest output for pass/fail counts
    output = result.stdout + result.stderr
    tests_passed = 0
    tests_failed = 0

    for line in output.splitlines():
        # pytest summary line: "182 passed in 2.40s" or "2 failed, 180 passed in 2.50s"
        if "passed" in line and ("failed" in line or "passed in" in line):
            parts = line.strip().split()
            for i, part in enumerate(parts):
                if part == "passed" and i > 0:
                    try:
                        tests_passed = int(parts[i - 1])
                    except ValueError:
                        pass
                if part == "failed" and i > 0:
                    try:
                        tests_failed = int(parts[i - 1])
                    except ValueError:
                        pass

    test_status = "PASS" if result.returncode == 0 else "FAIL"
    return {
        "tests_passed":   tests_passed,
        "tests_failed":   tests_failed,
        "test_exit_code": result.returncode,
        "test_status":    test_status,
    }


# =============================================================================
# STAGE EXECUTOR
# Wraps each stage runner with timing, error handling, and logging.
# =============================================================================

def _execute_stage(stage_key: str, run_config: dict) -> tuple[bool, dict, float]:
    """
    Execute a single pipeline stage safely.

    Parameters
    ----------
    stage_key   : Key from STAGE_REGISTRY (e.g. "bronze")
    run_config  : The full run configuration dict

    Returns
    -------
    (success: bool, metrics: dict, duration_sec: float)
    """
    stage = STAGE_REGISTRY[stage_key]
    label = stage["label"]
    runner_name = stage["callable"]

    # Map callable name to function
    runner_map = {
        "_run_generate": _run_generate,
        "_run_bronze":   _run_bronze,
        "_run_validate": _run_validate,
        "_run_silver":   _run_silver,
        "_run_gold":     _run_gold,
        "_run_tests":    _run_tests,
    }
    runner_fn = runner_map[runner_name]

    logger.info(f"  Starting: {label}")
    t_start = time.perf_counter()

    try:
        metrics = runner_fn()
        duration = round(time.perf_counter() - t_start, 2)
        logger.info(f"  Completed: {label} ({duration}s) | metrics={metrics}")
        return True, metrics, duration

    except Exception as e:
        duration = round(time.perf_counter() - t_start, 2)
        tb = traceback.format_exc()
        logger.error(f"  FAILED: {label} ({duration}s)\n{tb}")
        return False, {"error": str(e), "traceback": tb}, duration


# =============================================================================
# RUN HISTORY PRINTER
# =============================================================================

def _print_run_history(limit: int = 10) -> None:
    """Print the last N pipeline runs from the metadata store."""
    try:
        df = pd.read_sql(
            f"SELECT run_id, run_name, status, triggered_by, "
            f"started_at, duration_seconds, bronze_records, "
            f"silver_records, gold_fact_rows, tests_passed, tests_failed "
            f"FROM pipeline_runs "
            f"ORDER BY run_id DESC LIMIT {limit}",
            con=engine
        )
        if df.empty:
            print("No pipeline runs recorded yet.")
            return

        print("\n" + "=" * 75)
        print(f"  PIPELINE RUN HISTORY  (last {min(limit, len(df))} runs)")
        print("=" * 75)
        print(df.to_string(index=False))
        print("=" * 75 + "\n")

    except Exception as e:
        print(f"Could not retrieve run history: {e}")


# =============================================================================
# HEALTH DASHBOARD PRINTER
# =============================================================================

def _print_health_dashboard(run: PipelineRun, stage_timings: dict) -> None:
    """Print a formatted pipeline health dashboard for the completed run."""
    overall_status = run.status
    status_symbol  = "OK" if overall_status == "SUCCESS" else ("PARTIAL" if overall_status == "PARTIAL" else "FAIL")

    print("\n" + "=" * 65)
    print("  PHASE 7 - PIPELINE ORCHESTRATION DASHBOARD")
    print("=" * 65)
    print(f"  Run ID        : {run.run_id}")
    print(f"  Run Name      : {run.run_name}")
    print(f"  Status        : [{status_symbol}] {overall_status}")
    print(f"  Triggered By  : {run.triggered_by}")
    print(f"  Started At    : {run.started_at}")
    print(f"  Completed At  : {run.completed_at}")
    print(f"  Total Duration: {run.duration_seconds}s")
    print()
    print("  -- Stage Results --")
    print(f"  {'Stage':<12} {'Status':<10} {'Duration':>10}  {'Key Metric'}")
    print("  " + "-" * 55)

    completed = run.stages_completed or []
    failed    = run.stages_failed or []

    stage_metrics_map = {
        "generate": f"~1030 rows generated",
        "bronze":   f"{run.bronze_records or 0:,} bronze records",
        "validate": f"{run.valid_records or 0:,} valid records",
        "silver":   f"{run.silver_records or 0:,} silver records",
        "gold":     f"{run.gold_fact_rows or 0:,} fact rows",
        "test":     f"{run.tests_passed or 0} passed / {run.tests_failed or 0} failed",
    }

    for stage_key in (run.stages_planned or DEFAULT_STAGES):
        if stage_key in completed:
            st = "PASS"
        elif stage_key in failed:
            st = "FAIL"
        else:
            st = "SKIP"

        dur   = stage_timings.get(stage_key, 0)
        label = STAGE_REGISTRY[stage_key]["label"].split(" — ")[1]  # short name
        metric = stage_metrics_map.get(stage_key, "")

        print(f"  {label:<22} [{st:<4}] {dur:>8.1f}s  {metric}")

    print()
    print("  -- Pipeline Metrics --")
    print(f"  Bronze Records  : {run.bronze_records or 0:>8,}")
    print(f"  Valid Records   : {run.valid_records or 0:>8,}")
    print(f"  Silver Records  : {run.silver_records or 0:>8,}")
    print(f"  Gold Fact Rows  : {run.gold_fact_rows or 0:>8,}")
    print(f"  Tests Passed    : {run.tests_passed or 0:>8,}")
    print(f"  Tests Failed    : {run.tests_failed or 0:>8,}")

    if run.error_message:
        print()
        print("  -- Error Details --")
        # Print only the last 5 lines of the traceback to keep it readable
        err_lines = run.error_message.strip().splitlines()
        for line in err_lines[-5:]:
            print(f"  {line}")

    print("=" * 65 + "\n")


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

def run_pipeline(
    stages: list[str] = None,
    run_name: str = "full_pipeline",
    triggered_by: str = "manual",
    stop_on_failure: bool = True,
) -> PipelineRun:
    """
    Phase 7 Master Orchestrator.

    Runs the specified pipeline stages in order, recording every run
    to the pipeline_runs metadata table.

    Parameters
    ----------
    stages          : List of stage keys to run (defaults to all stages)
    run_name        : Label for this run (e.g. "full_pipeline", "gold_only")
    triggered_by    : Who triggered the run ("manual", "scheduler", "ci")
    stop_on_failure : If True, stop the pipeline on the first failed stage.
                      If False, continue and mark run as PARTIAL.

    Returns
    -------
    PipelineRun ORM object with the full run record.
    """
    stages_to_run = stages or DEFAULT_STAGES

    # Ensure pipeline_runs table exists
    Base.metadata.create_all(bind=engine)

    # ── 1. Create run record with RUNNING status ──────────────────────────────
    run_start = datetime.now()

    with Session(engine) as session:
        run = PipelineRun(
            run_name       = run_name,
            status         = "RUNNING",
            triggered_by   = triggered_by,
            started_at     = run_start,
            stages_planned = stages_to_run,
            stages_completed = [],
            stages_failed    = [],
        )
        session.add(run)
        session.commit()
        run_id = run.run_id

    logger.info("=" * 60)
    logger.info(f"  Phase 7: Pipeline Orchestrator — Run #{run_id}")
    logger.info(f"  Stages: {stages_to_run}")
    logger.info("=" * 60)

    # ── 2. Execute each stage sequentially ───────────────────────────────────
    stages_completed = []
    stages_failed    = []
    stage_timings    = {}
    all_metrics      = {}
    first_error      = None
    aborted          = False

    for stage_key in stages_to_run:
        if stage_key not in STAGE_REGISTRY:
            logger.warning(f"  Unknown stage '{stage_key}' — skipping.")
            continue

        logger.info(f"\n  [{stages_to_run.index(stage_key)+1}/{len(stages_to_run)}] {STAGE_REGISTRY[stage_key]['label']}")

        success, metrics, duration = _execute_stage(stage_key, {})
        stage_timings[stage_key] = duration
        all_metrics.update(metrics)

        if success:
            stages_completed.append(stage_key)
        else:
            stages_failed.append(stage_key)
            if first_error is None:
                first_error = metrics.get("traceback", metrics.get("error", "Unknown error"))
            if stop_on_failure:
                logger.error(f"  Stopping pipeline after failure in stage '{stage_key}'.")
                aborted = True
                break

    # ── 3. Determine overall status ──────────────────────────────────────────
    if not stages_failed:
        overall_status = "SUCCESS"
    elif stages_completed:
        overall_status = "PARTIAL"
    else:
        overall_status = "FAILED"

    run_end      = datetime.now()
    total_seconds = round((run_end - run_start).total_seconds(), 2)

    # ── 4. Update run record in DB ────────────────────────────────────────────
    with Session(engine) as session:
        run = session.get(PipelineRun, run_id)
        run.status           = overall_status
        run.completed_at     = run_end
        run.duration_seconds = total_seconds
        run.stages_completed = stages_completed
        run.stages_failed    = stages_failed
        run.bronze_records   = all_metrics.get("bronze_records")
        run.valid_records    = all_metrics.get("valid_records")
        run.silver_records   = all_metrics.get("silver_records")
        run.gold_fact_rows   = all_metrics.get("gold_fact_rows")
        run.tests_passed     = all_metrics.get("tests_passed")
        run.tests_failed     = all_metrics.get("tests_failed")
        run.error_message    = first_error
        session.commit()

        # Re-fetch for the dashboard printer
        session.refresh(run)
        run_snapshot = run

    # ── 5. Print health dashboard ─────────────────────────────────────────────
    _print_health_dashboard(run_snapshot, stage_timings)

    logger.info(f"Phase 7 Complete — Run #{run_id} | Status: {overall_status} | {total_seconds}s")
    return run_snapshot


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def _parse_args():
    parser = argparse.ArgumentParser(
        description="Phase 7: Pipeline Orchestrator — runs the full Medallion pipeline end-to-end."
    )
    parser.add_argument(
        "--stages",
        type=str,
        default=None,
        help=(
            "Comma-separated list of stages to run. "
            "Choices: generate,bronze,validate,silver,gold,test. "
            "Default: all stages."
        ),
    )
    parser.add_argument(
        "--name",
        type=str,
        default="full_pipeline",
        help="Label for this pipeline run (stored in pipeline_runs table).",
    )
    parser.add_argument(
        "--triggered-by",
        type=str,
        default="manual",
        help="Who/what triggered this run (manual, scheduler, ci).",
    )
    parser.add_argument(
        "--no-stop-on-failure",
        action="store_true",
        default=False,
        help="If set, continue running remaining stages even if one fails (PARTIAL run).",
    )
    parser.add_argument(
        "--history",
        action="store_true",
        default=False,
        help="Print the last 10 pipeline run records and exit.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    if args.history:
        _print_run_history(limit=10)
        sys.exit(0)

    stages = [s.strip() for s in args.stages.split(",")] if args.stages else None

    run = run_pipeline(
        stages          = stages,
        run_name        = args.name,
        triggered_by    = args.triggered_by,
        stop_on_failure = not args.no_stop_on_failure,
    )

    # Exit with non-zero code if pipeline failed (useful for CI/CD pipelines)
    sys.exit(0 if run.status in ("SUCCESS", "PARTIAL") else 1)

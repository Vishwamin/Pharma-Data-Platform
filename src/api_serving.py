"""
Phase 8: Clinical Data Serving Layer — FastAPI REST Service
============================================================
Exposes the Gold Layer Star Schema and Phase 7 Pipeline Metadata
via high-performance, production-ready REST API endpoints.

Endpoints:
  - GET  /                           : API Root & service information
  - GET  /health                     : Database health check & pipeline telemetry
  - GET  /api/v1/kpis                : Executive clinical trial KPIs
  - GET  /api/v1/drugs/efficacy      : Comparative efficacy & success rates by drug
  - GET  /api/v1/demographics/summary: Patient demographics by country & gender
  - GET  /api/v1/trials/summary      : Clinical trials duration & patient volume
  - GET  /api/v1/pipeline/runs       : Historical pipeline executions from metadata store
  - POST /api/v1/pipeline/trigger    : Webhook endpoint to trigger pipeline runs

Run locally:
  uvicorn src.api_serving:app --host 127.0.0.1 --port 8000 --reload
"""

import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

import pandas as pd
from sqlalchemy import text
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure project root is in Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.config import Config
from src.logger import get_logger
from src.database import engine
from src.orchestrator import run_pipeline

logger = get_logger("ClinicalAPIServing")

# -----------------------------------------------------------------------------
# FastAPI App Initialization
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Pharma Clinical Trial Analytics API",
    description=(
        "Production Data Serving Layer delivering analytical metrics from "
        "the Medallion Gold Layer Star Schema and Phase 7 Pipeline Metadata."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for dashboard & frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Pydantic Response Models
# -----------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    database: str
    timestamp: datetime
    gold_records_count: int
    latest_pipeline_run: Optional[Dict[str, Any]] = None


class ClinicalKPIs(BaseModel):
    total_fact_records: int
    unique_patients: int
    unique_trials: int
    unique_drugs: int
    overall_positive_rate_pct: float
    avg_treatment_duration_days: float
    avg_dosage_mg: float


class DrugEfficacyItem(BaseModel):
    drug_id: str
    drug_name: str
    total_trials: int
    positive_outcomes: int
    success_rate_pct: float
    avg_dosage_mg: float


class CountryDemographicItem(BaseModel):
    country: str
    patient_count: int
    positive_outcomes: int
    success_rate_pct: float


class GenderDemographicItem(BaseModel):
    gender: str
    patient_count: int
    avg_age: float


class DemographicsSummary(BaseModel):
    by_country: List[CountryDemographicItem]
    by_gender: List[GenderDemographicItem]


class TrialSummaryItem(BaseModel):
    trial_id: str
    treatment: str
    duration_days: Optional[int]
    patient_count: int
    success_rate_pct: float


class TriggerRunRequest(BaseModel):
    run_name: str = Field(default="api_triggered_run", description="Name label for pipeline run")
    stages: Optional[List[str]] = Field(default=None, description="Optional list of stages: generate, bronze, validate, silver, gold, test")


class TriggerRunResponse(BaseModel):
    message: str
    run_name: str
    triggered_at: datetime
    stages_requested: List[str]


# -----------------------------------------------------------------------------
# Helper Database Query Runner
# -----------------------------------------------------------------------------
def _query_df(sql: str) -> pd.DataFrame:
    """Execute raw SQL query against configured database and return DataFrame."""
    try:
        return pd.read_sql(sql, con=engine)
    except Exception as exc:
        logger.error(f"Database query failed: {sql} | Error: {str(exc)}")
        raise HTTPException(status_code=500, detail=f"Database query error: {str(exc)}")


# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------
@app.get("/", tags=["System"])
def root() -> Dict[str, Any]:
    """Root endpoint with service identity and documentation paths."""
    return {
        "service": "Pharma Clinical Trial Analytics Data Serving Layer",
        "version": "1.0.0",
        "architecture": "Medallion (Bronze -> Silver -> Gold Star Schema)",
        "docs_url": "/docs",
        "health_check": "/health",
        "api_endpoints": [
            "/api/v1/kpis",
            "/api/v1/drugs/efficacy",
            "/api/v1/demographics/summary",
            "/api/v1/trials/summary",
            "/api/v1/pipeline/runs",
            "/api/v1/pipeline/trigger",
        ],
    }


@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check() -> HealthResponse:
    """System health check verifying database connectivity and latest pipeline telemetry."""
    # Test DB connection
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    # Check Gold layer row count
    count_df = _query_df("SELECT COUNT(*) as count FROM fact_clinical_outcomes")
    gold_count = int(count_df["count"].iloc[0]) if not count_df.empty else 0

    # Retrieve latest pipeline run from Phase 7 metadata store
    latest_run = None
    try:
        run_df = _query_df(
            "SELECT run_id, run_name, status, duration_seconds, started_at, completed_at "
            "FROM pipeline_runs ORDER BY run_id DESC LIMIT 1"
        )
        if not run_df.empty:
            latest_run = run_df.to_dict(orient="records")[0]
            if latest_run.get("started_at"):
                latest_run["started_at"] = str(latest_run["started_at"])
            if latest_run.get("completed_at"):
                latest_run["completed_at"] = str(latest_run["completed_at"])
    except Exception:
        latest_run = None

    db_type = "PostgreSQL" if "postgresql" in str(engine.url) else "SQLite"

    return HealthResponse(
        status="HEALTHY",
        database=f"{db_type} ({engine.url.database})",
        timestamp=datetime.now(),
        gold_records_count=gold_count,
        latest_pipeline_run=latest_run,
    )


@app.get("/api/v1/kpis", response_model=ClinicalKPIs, tags=["Clinical Analytics"])
def get_clinical_kpis() -> ClinicalKPIs:
    """Retrieve top-level clinical performance KPIs derived from Gold Star Schema."""
    sql = """
    SELECT
        COUNT(*) as total_fact_records,
        COUNT(DISTINCT patient_key) as unique_patients,
        COUNT(DISTINCT trial_key) as unique_trials,
        COUNT(DISTINCT drug_key) as unique_drugs,
        ROUND((AVG(outcome_binary) * 100)::NUMERIC, 2) as overall_positive_rate_pct,
        ROUND(AVG(treatment_duration_days)::NUMERIC, 1) as avg_treatment_duration_days,
        ROUND(AVG(dosage)::NUMERIC, 2) as avg_dosage_mg
    FROM fact_clinical_outcomes
    """
    # SQLite fallback for ROUND without NUMERIC cast
    if "sqlite" in str(engine.url):
        sql = """
        SELECT
            COUNT(*) as total_fact_records,
            COUNT(DISTINCT patient_key) as unique_patients,
            COUNT(DISTINCT trial_key) as unique_trials,
            COUNT(DISTINCT drug_key) as unique_drugs,
            ROUND(AVG(outcome_binary) * 100, 2) as overall_positive_rate_pct,
            ROUND(AVG(treatment_duration_days), 1) as avg_treatment_duration_days,
            ROUND(AVG(dosage), 2) as avg_dosage_mg
        FROM fact_clinical_outcomes
        """
    df = _query_df(sql)
    if df.empty or df["total_fact_records"].iloc[0] == 0:
        raise HTTPException(status_code=404, detail="No clinical data found in Gold Layer.")

    row = df.iloc[0]
    return ClinicalKPIs(
        total_fact_records=int(row["total_fact_records"]),
        unique_patients=int(row["unique_patients"]),
        unique_trials=int(row["unique_trials"]),
        unique_drugs=int(row["unique_drugs"]),
        overall_positive_rate_pct=float(row["overall_positive_rate_pct"] or 0.0),
        avg_treatment_duration_days=float(row["avg_treatment_duration_days"] or 0.0),
        avg_dosage_mg=float(row["avg_dosage_mg"] or 0.0),
    )


@app.get("/api/v1/drugs/efficacy", response_model=List[DrugEfficacyItem], tags=["Clinical Analytics"])
def get_drug_efficacy(
    min_trials: int = Query(default=0, description="Filter drugs with minimum trial count")
) -> List[DrugEfficacyItem]:
    """Calculate comparative treatment success rates and dosages per investigational drug."""
    cast_sql = "::NUMERIC" if "postgresql" in str(engine.url) else ""
    sql = f"""
    SELECT
        d.drug_id,
        d.drug_name,
        COUNT(*) as total_trials,
        SUM(f.outcome_binary) as positive_outcomes,
        ROUND((AVG(f.outcome_binary) * 100){cast_sql}, 1) as success_rate_pct,
        ROUND(AVG(f.dosage){cast_sql}, 2) as avg_dosage_mg
    FROM fact_clinical_outcomes f
    JOIN dim_drug d ON f.drug_key = d.drug_key
    GROUP BY d.drug_id, d.drug_name
    HAVING COUNT(*) >= {min_trials}
    ORDER BY success_rate_pct DESC
    """
    df = _query_df(sql)
    items = []
    for _, row in df.iterrows():
        items.append(
            DrugEfficacyItem(
                drug_id=str(row["drug_id"]),
                drug_name=str(row["drug_name"]),
                total_trials=int(row["total_trials"]),
                positive_outcomes=int(row["positive_outcomes"] or 0),
                success_rate_pct=float(row["success_rate_pct"] or 0.0),
                avg_dosage_mg=float(row["avg_dosage_mg"] or 0.0),
            )
        )
    return items


@app.get("/api/v1/demographics/summary", response_model=DemographicsSummary, tags=["Clinical Analytics"])
def get_demographics_summary() -> DemographicsSummary:
    """Retrieve patient demographic breakdown across countries and gender cohorts."""
    cast_sql = "::NUMERIC" if "postgresql" in str(engine.url) else ""

    # Country breakdown
    country_sql = f"""
    SELECT
        p.country,
        COUNT(*) as patient_count,
        SUM(f.outcome_binary) as positive_outcomes,
        ROUND((AVG(f.outcome_binary) * 100){cast_sql}, 1) as success_rate_pct
    FROM fact_clinical_outcomes f
    JOIN dim_patient p ON f.patient_key = p.patient_key
    GROUP BY p.country
    ORDER BY patient_count DESC
    """
    df_country = _query_df(country_sql)
    by_country = [
        CountryDemographicItem(
            country=str(r["country"]),
            patient_count=int(r["patient_count"]),
            positive_outcomes=int(r["positive_outcomes"] or 0),
            success_rate_pct=float(r["success_rate_pct"] or 0.0),
        )
        for _, r in df_country.iterrows()
    ]

    # Gender breakdown
    gender_sql = f"""
    SELECT
        p.gender,
        COUNT(*) as patient_count,
        ROUND(AVG(p.age){cast_sql}, 1) as avg_age
    FROM fact_clinical_outcomes f
    JOIN dim_patient p ON f.patient_key = p.patient_key
    GROUP BY p.gender
    ORDER BY patient_count DESC
    """
    df_gender = _query_df(gender_sql)
    by_gender = [
        GenderDemographicItem(
            gender=str(r["gender"]),
            patient_count=int(r["patient_count"]),
            avg_age=float(r["avg_age"] or 0.0),
        )
        for _, r in df_gender.iterrows()
    ]

    return DemographicsSummary(by_country=by_country, by_gender=by_gender)


@app.get("/api/v1/trials/summary", response_model=List[TrialSummaryItem], tags=["Clinical Analytics"])
def get_trials_summary() -> List[TrialSummaryItem]:
    """Retrieve summary metrics per clinical trial including patient enrollment and duration."""
    cast_sql = "::NUMERIC" if "postgresql" in str(engine.url) else ""
    sql = f"""
    SELECT
        t.trial_id,
        t.treatment,
        t.treatment_duration_days as duration_days,
        COUNT(*) as patient_count,
        ROUND((AVG(f.outcome_binary) * 100){cast_sql}, 1) as success_rate_pct
    FROM fact_clinical_outcomes f
    JOIN dim_trial t ON f.trial_key = t.trial_key
    GROUP BY t.trial_id, t.treatment, t.treatment_duration_days
    ORDER BY patient_count DESC
    """
    df = _query_df(sql)
    return [
        TrialSummaryItem(
            trial_id=str(r["trial_id"]),
            treatment=str(r["treatment"]),
            duration_days=int(r["duration_days"]) if pd.notna(r["duration_days"]) else None,
            patient_count=int(r["patient_count"]),
            success_rate_pct=float(r["success_rate_pct"] or 0.0),
        )
        for _, r in df.iterrows()
    ]


@app.get("/api/v1/pipeline/runs", tags=["Pipeline Telemetry"])
def get_pipeline_runs(limit: int = Query(default=10, ge=1, le=50)) -> List[Dict[str, Any]]:
    """Retrieve historical pipeline execution metadata from the Phase 7 metadata store."""
    sql = f"""
    SELECT
        run_id, run_name, status, triggered_by,
        started_at, completed_at, duration_seconds,
        stages_planned, stages_completed, stages_failed,
        bronze_records, valid_records, silver_records, gold_fact_rows,
        tests_passed, tests_failed, error_message
    FROM pipeline_runs
    ORDER BY run_id DESC
    LIMIT {limit}
    """
    df = _query_df(sql)
    records = df.to_dict(orient="records")
    for r in records:
        if r.get("started_at"):
            r["started_at"] = str(r["started_at"])
        if r.get("completed_at"):
            r["completed_at"] = str(r["completed_at"])
    return records


@app.post("/api/v1/pipeline/trigger", response_model=TriggerRunResponse, tags=["Pipeline Telemetry"])
def trigger_pipeline_run(
    payload: TriggerRunRequest,
    background_tasks: BackgroundTasks,
) -> TriggerRunResponse:
    """Trigger an asynchronous execution of the Medallion pipeline via webhook."""
    stages = payload.stages or ["generate", "bronze", "validate", "silver", "gold", "test"]

    # Launch in background thread so HTTP response returns immediately
    background_tasks.add_task(
        run_pipeline,
        stages=stages,
        run_name=payload.run_name,
        triggered_by="api_webhook",
        stop_on_failure=True,
    )

    logger.info(f"Pipeline run triggered via API: run_name='{payload.run_name}', stages={stages}")

    return TriggerRunResponse(
        message="Pipeline run successfully scheduled in background.",
        run_name=payload.run_name,
        triggered_at=datetime.now(),
        stages_requested=stages,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api_serving:app", host="127.0.0.1", port=8000, reload=True)

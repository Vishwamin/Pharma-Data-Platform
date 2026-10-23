"""
Phase 8: Interactive Clinical Intelligence & Observability Dashboard
====================================================================
Streamlit web dashboard providing analytical visibility into the
Gold Layer Star Schema and Phase 7 Pipeline Observability telemetry.

Features:
  - Executive KPI scorecards (Total Patients, Positive Rate %, Trials, Duration)
  - Interactive multi-parameter filtering (Trial, Country, Drug)
  - Drug efficacy comparative analytics & dosage analysis
  - Patient cohort demographic distribution (Country & Gender)
  - Real-time pipeline health telemetry from 'pipeline_runs' metadata store

Launch dashboard:
  streamlit run src/dashboard.py
"""

import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import text
import streamlit as st

# Ensure project root is in Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.config import Config
from src.database import engine

# -----------------------------------------------------------------------------
# Streamlit Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Clinical Data Platform | Intelligence & Observability",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border-radius: 8px;
        padding: 1rem;
        border-left: 4px solid #3B82F6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Cached Database Query Helpers
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60)
def load_gold_dataset() -> pd.DataFrame:
    """Load denormalized Gold Layer view for analytical slicing and filtering."""
    sql = """
    SELECT
        f.fact_id,
        f.dosage,
        f.treatment_duration_days,
        f.outcome,
        f.outcome_binary,
        f.outcome_category,
        p.patient_id,
        p.age,
        p.gender,
        p.country,
        t.trial_id,
        t.treatment,
        d.drug_id,
        d.drug_name
    FROM fact_clinical_outcomes f
    JOIN dim_patient p ON f.patient_key = p.patient_key
    JOIN dim_trial t   ON f.trial_key   = t.trial_key
    JOIN dim_drug d    ON f.drug_key    = d.drug_key
    """
    try:
        return pd.read_sql(sql, con=engine)
    except Exception as exc:
        st.error(f"Failed to load Gold layer data: {exc}")
        return pd.DataFrame()


@st.cache_data(ttl=30)
def load_pipeline_runs() -> pd.DataFrame:
    """Fetch pipeline execution telemetry from Phase 7 metadata store."""
    sql = """
    SELECT
        run_id, run_name, status, triggered_by,
        started_at, completed_at, duration_seconds,
        bronze_records, valid_records, silver_records, gold_fact_rows,
        tests_passed, tests_failed
    FROM pipeline_runs
    ORDER BY run_id DESC
    LIMIT 20
    """
    try:
        return pd.read_sql(sql, con=engine)
    except Exception:
        return pd.DataFrame()


# -----------------------------------------------------------------------------
# Main Dashboard Application
# -----------------------------------------------------------------------------
df_gold = load_gold_dataset()
df_runs = load_pipeline_runs()

# Title and Header
st.markdown('<div class="main-header">🧬 Clinical Trial Intelligence & Observability Hub</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">End-to-end Medallion Architecture Serving Layer — Gold Layer Star Schema & Pipeline Telemetry</div>',
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Sidebar: Database Status & Interactive Filters
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Platform Control")

    db_type = "PostgreSQL" if "postgresql" in str(engine.url) else "SQLite Fallback"
    st.info(f"**Database:** {db_type}\n\n**Schema Tier:** Gold Layer (Star Schema)")

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.subheader("🔍 Cohort Slicing & Filters")

    if not df_gold.empty:
        # Filter by Trial
        trials_available = ["All"] + sorted(df_gold["trial_id"].dropna().unique().tolist())
        selected_trial = st.selectbox("Clinical Trial ID", trials_available)

        # Filter by Drug
        drugs_available = ["All"] + sorted(df_gold["drug_name"].dropna().unique().tolist())
        selected_drug = st.selectbox("Investigational Drug", drugs_available)

        # Filter by Country
        countries_available = ["All"] + sorted(df_gold["country"].dropna().unique().tolist())
        selected_country = st.selectbox("Patient Country", countries_available)

        # Apply Filters
        filtered_df = df_gold.copy()
        if selected_trial != "All":
            filtered_df = filtered_df[filtered_df["trial_id"] == selected_trial]
        if selected_drug != "All":
            filtered_df = filtered_df[filtered_df["drug_name"] == selected_drug]
        if selected_country != "All":
            filtered_df = filtered_df[filtered_df["country"] == selected_country]
    else:
        filtered_df = pd.DataFrame()

    st.markdown("---")
    st.caption("Phase 8 Data Serving Layer | Pharma Data Engineering Platform")


# Check data availability
if df_gold.empty:
    st.warning("⚠️ No Gold layer data found in database. Run `python src/orchestrator.py` to populate tables.")
    st.stop()


# -----------------------------------------------------------------------------
# Main Content: Tabs
# -----------------------------------------------------------------------------
tab_kpis, tab_drugs, tab_demographics, tab_observability = st.tabs([
    "📊 Executive KPIs",
    "💊 Drug Efficacy Explorer",
    "🌍 Patient Demographics",
    "🛠️ Pipeline Observability",
])

# ─── TAB 1: EXECUTIVE KPIS ───────────────────────────────────────────────────
with tab_kpis:
    st.subheader("Executive Clinical Metrics")

    # Metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    total_records = len(filtered_df)
    unique_patients = filtered_df["patient_id"].nunique()
    pos_rate = (filtered_df["outcome_binary"].mean() * 100) if total_records > 0 else 0.0
    avg_duration = filtered_df["treatment_duration_days"].mean() if total_records > 0 else 0.0
    avg_dosage = filtered_df["dosage"].mean() if total_records > 0 else 0.0

    col1.metric("Enrolled Patients", f"{unique_patients:,}")
    col2.metric("Positive Outcome Rate", f"{pos_rate:.1f}%")
    col3.metric("Avg Treatment Duration", f"{avg_duration:.0f} days")
    col4.metric("Avg Dosage", f"{avg_dosage:.1f} mg")
    col5.metric("Active Trials Count", f"{filtered_df['trial_id'].nunique()}")

    st.markdown("---")

    # Distribution charts
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("##### Clinical Outcomes Distribution")
        outcome_counts = filtered_df["outcome_category"].value_counts().reset_index()
        outcome_counts.columns = ["Outcome Category", "Count"]
        st.bar_chart(outcome_counts.set_index("Outcome Category"))

    with chart_col2:
        st.markdown("##### Enrollment by Clinical Trial")
        trial_counts = filtered_df["trial_id"].value_counts().reset_index()
        trial_counts.columns = ["Trial ID", "Patients"]
        st.bar_chart(trial_counts.set_index("Trial ID"))


# ─── TAB 2: DRUG EFFICACY EXPLORER ───────────────────────────────────────────
with tab_drugs:
    st.subheader("Investigational Drug Performance & Efficacy")

    drug_summary = (
        filtered_df.groupby("drug_name")
        .agg(
            total_trials=("fact_id", "count"),
            positive_outcomes=("outcome_binary", "sum"),
            success_rate_pct=("outcome_binary", lambda x: round(x.mean() * 100, 1)),
            avg_dosage_mg=("dosage", lambda x: round(x.mean(), 1)),
            avg_duration_days=("treatment_duration_days", lambda x: round(x.mean(), 1)),
        )
        .reset_index()
        .sort_values(by="success_rate_pct", ascending=False)
    )

    st.dataframe(
        drug_summary.rename(
            columns={
                "drug_name": "Drug Name",
                "total_trials": "Total Trials",
                "positive_outcomes": "Positive Outcomes",
                "success_rate_pct": "Success Rate (%)",
                "avg_dosage_mg": "Avg Dosage (mg)",
                "avg_duration_days": "Avg Duration (days)",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("##### Comparative Success Rate by Drug")
    st.bar_chart(drug_summary.set_index("drug_name")["success_rate_pct"])


# ─── TAB 3: PATIENT DEMOGRAPHICS ─────────────────────────────────────────────
with tab_demographics:
    st.subheader("Patient Cohort Breakdown")

    demo_col1, demo_col2 = st.columns(2)

    with demo_col1:
        st.markdown("##### Geographic Distribution (Top Countries)")
        country_agg = (
            filtered_df.groupby("country")
            .agg(
                patient_count=("patient_id", "count"),
                success_rate_pct=("outcome_binary", lambda x: round(x.mean() * 100, 1)),
            )
            .reset_index()
            .sort_values(by="patient_count", ascending=False)
        )
        st.dataframe(country_agg, use_container_width=True, hide_index=True)
        st.bar_chart(country_agg.set_index("country")["patient_count"])

    with demo_col2:
        st.markdown("##### Gender Cohort & Age Profile")
        gender_agg = (
            filtered_df.groupby("gender")
            .agg(
                patient_count=("patient_id", "count"),
                avg_age=("age", lambda x: round(x.mean(), 1)),
                success_rate_pct=("outcome_binary", lambda x: round(x.mean() * 100, 1)),
            )
            .reset_index()
        )
        st.dataframe(gender_agg, use_container_width=True, hide_index=True)
        st.bar_chart(gender_agg.set_index("gender")["patient_count"])


# ─── TAB 4: PIPELINE OBSERVABILITY ───────────────────────────────────────────
with tab_observability:
    st.subheader("Phase 7 Pipeline Run Telemetry & Health Audit")

    if not df_runs.empty:
        obs_col1, obs_col2, obs_col3 = st.columns(3)
        total_runs = len(df_runs)
        successful_runs = (df_runs["status"] == "SUCCESS").sum()
        latest_status = df_runs["status"].iloc[0]

        obs_col1.metric("Total Executions Logged", total_runs)
        obs_col2.metric("Successful Executions", f"{successful_runs} / {total_runs}")
        obs_col3.metric("Latest Run Status", latest_status)

        st.markdown("##### Recent Execution Log")
        st.dataframe(
            df_runs[[
                "run_id", "run_name", "status", "triggered_by",
                "started_at", "duration_seconds", "gold_fact_rows",
                "tests_passed", "tests_failed"
            ]].rename(
                columns={
                    "run_id": "Run ID",
                    "run_name": "Run Name",
                    "status": "Status",
                    "triggered_by": "Triggered By",
                    "started_at": "Timestamp",
                    "duration_seconds": "Duration (s)",
                    "gold_fact_rows": "Gold Records",
                    "tests_passed": "Tests Passed",
                    "tests_failed": "Tests Failed",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("##### Execution Duration Trend (Seconds)")
        st.line_chart(df_runs.sort_values(by="run_id").set_index("run_id")["duration_seconds"])
    else:
        st.info("No pipeline run records found. Execute `python src/orchestrator.py` to populate telemetry.")

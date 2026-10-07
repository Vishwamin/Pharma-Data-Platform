# Enterprise Pharma Clinical Data Engineering Pipeline

An end-to-end Medallion-Architecture Data Pipeline built for Clinical Trial Analytics.

---

## 🏛 Architecture Overview (Medallion Architecture)

```
                       [ RAW CSV SOURCE FILES ]
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │ Phase 1: Python Ingestion    │
                   │ & Config Management          │
                   └──────────────┬───────────────┘
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │ Phase 2: BRONZE LAYER        │
                   │ Raw Storage (PostgreSQL DB)  │
                   └──────────────┬───────────────┘
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │ Phase 3: DATA VALIDATION     │
                   │ Quality Rules & Quarantine   │
                   └──────────────┬───────────────┘
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │ Phase 3.5: SQL ANALYTICS     │
                   │ PostgreSQL Engineering Engine│
                   └──────────────┬───────────────┘
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │ Phase 4: SILVER LAYER        │
                   │ PySpark Transformations      │
                   └──────────────────────────────┘
```

---

## 📋 Completed Pipeline Phases

### 🔹 PHASE 1: Project Foundation, Synthetic Data & Raw Ingestion
- **Goal**: Set up production directory structure, logging infrastructure, environment configuration, realistic synthetic clinical dataset, and raw string ingestion.
- **What We Built**:
  - `config/config.py`: Centralized environment loader using `python-dotenv` for path and parameter management.
  - `src/logger.py`: Production dual-handler stream and persistent file logger (`logs/pipeline.log`).
  - `src/generate_synthetic_data.py`: Synthetic dataset generator producing clinical records with intentional data quality issues (nulls, duplicates, invalid ages, date errors, malformed dosages).
  - `src/ingest.py`: Raw CSV string loader that verifies file existence, size, and structural schema presence.

---

### 🔹 PHASE 2: Database Layer & Bronze Storage Landing
- **Goal**: Establish the raw database storage layer (Bronze Layer) using SQLAlchemy with PostgreSQL / local database fallback.
- **What We Built**:
  - `src/database.py`: SQLAlchemy engine management, session pooling, health checks, and database fallback handler.
  - `src/models_bronze.py`: `BronzeClinicalTrials` ORM table schema preserving raw string data and audit metadata (`ingestion_timestamp`, `source_file_name`).
  - `src/load_bronze.py`: Ingestion pipeline loading raw CSV string payloads into the Bronze database table in batch chunks.

---

### 🔹 PHASE 3: Data Validation & Data Quality Rules Engine
- **Goal**: Build an automated Data Quality Rules Engine to audit Bronze records, enforce business logic, standardize categoricals, deduplicate records, and isolate corrupted data into a Quarantine table.
- **What We Built**:
  - `src/models_quarantine.py`: `QuarantineClinicalTrials` ORM table schema storing invalid records along with precise violation reasons (`violation_reasons`).
  - `src/validation.py`: Rule-based validation engine applying null checks, age bounds validation (18-100), dosage range limits (0-500mg), date chronological sanity (`end_date >= start_date`), categorical standardization (`US` ➔ `USA`, `M` ➔ `Male`), and deduplication (`patient_id` + `trial_id`).

---

### 🔹 PHASE 3.5: SQL Analytics & PostgreSQL Engineering Engine
- **Goal**: Master production SQL and relational database engineering using our active PostgreSQL `pharma_clinical_db` database across 16 core data engineering dimensions.
- **What We Built**:
  - Modular SQL Scripts (`sql/01_basic_queries.sql` to `sql/09_pharma_clinical_analytics.sql`).
  - `src/run_sql_analytics.py`: Automated Python runner executing SQL analytics modules against PostgreSQL.
  - Advanced Querying: Window functions (`ROW_NUMBER`, `RANK`, `DENSE_RANK`, `LAG`, `LEAD`), CTEs, CASE statements, NULL profiling, B-Tree Indexing, and Query Optimization (`EXPLAIN ANALYZE`).

---

### 🔹 PHASE 4: PySpark Transformations & Silver Layer Conformed Landing
- **Goal**: Process validated clinical trial data through PySpark DataFrame transformations to build the Silver Layer in Medallion Architecture.
- **What We Built**:
  - `src/models_silver.py`: `SilverClinicalTrials` ORM table schema with enforced datatypes (Integer `age`, Float `dosage`, SQL Date `start_date`/`end_date`, derived `treatment_duration_days`).
  - `src/spark_silver.py`: PySpark DataFrame transformation engine performing type casting, window deduplication (`Window.partitionBy`), feature calculation (`datediff`), loading `silver_clinical_trials` PostgreSQL table, and exporting partitioned Parquet data lake files.

---

## 📂 Project Directory Structure

```
pharma-data-pipeline/
├── config/
│   ├── __init__.py
│   └── config.py               # Central configuration & DB settings
├── data/
│   ├── raw/
│   │   └── clinical_trials_raw.csv  # Raw landed data
│   ├── silver/
│   │   └── clinical_trials_parquet/ # Partitioned Parquet Data Lake
│   └── pharma_clinical_db.db        # Local database storage
├── logs/
│   └── pipeline.log            # Persistent audit logs
├── sql/
│   ├── 01_basic_queries.sql
│   ├── 02_aggregations_and_grouping.sql
│   ├── 03_case_statements.sql
│   ├── 04_joins_and_relational.sql
│   ├── 05_subqueries_and_ctes.sql
│   ├── 06_window_functions.sql
│   ├── 07_data_quality_and_deduplication.sql
│   ├── 08_indexing_transactions_optimization.sql
│   └── 09_pharma_clinical_analytics.sql
├── src/
│   ├── __init__.py
│   ├── database.py             # SQLAlchemy DB engine & connection manager
│   ├── generate_synthetic_data.py  # Synthetic clinical data generator
│   ├── ingest.py               # Raw file ingestion module
│   ├── load_bronze.py          # Bronze pipeline loader
│   ├── logger.py               # Production logging utility
│   ├── models_bronze.py        # SQLAlchemy Bronze layer ORM model
│   ├── models_quarantine.py    # SQLAlchemy Quarantine table ORM model
│   ├── models_silver.py        # SQLAlchemy Silver layer ORM model
│   ├── run_sql_analytics.py    # SQL analytics execution engine
│   ├── spark_silver.py         # PySpark Silver Transformation Engine
│   └── validation.py           # Data Quality Rules & Quarantine Engine
├── tests/                      # Unit & pipeline test suites
├── .env.example
├── .gitignore
├── README.md                   # Project documentation
└── requirements.txt            # Python dependencies
```

---

## 🚀 Execution Instructions

1. **Activate Virtual Environment**:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

2. **Generate Raw Synthetic Clinical Data (Phase 1)**:
   ```powershell
   python src/generate_synthetic_data.py
   ```

3. **Ingest & Load Raw Data into Bronze Database (Phase 2)**:
   ```powershell
   python src/load_bronze.py
   ```

4. **Run Data Validation & Quality Quarantine Engine (Phase 3)**:
   ```powershell
   python src/validation.py
   ```

5. **Run PostgreSQL Analytics Engine (Phase 3.5)**:
   ```powershell
   python src/run_sql_analytics.py
   ```

6. **Run PySpark Transformations to Silver Layer (Phase 4)**:
   ```powershell
   python src/spark_silver.py
   ```

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
                   └──────────────┬───────────────┘
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │ Phase 5: GOLD LAYER          │
                   │ Star Schema Analytical Model │
                   │  dim_patient  dim_trial      │
                   │  dim_drug     fact_outcomes  │
                   └──────────────┬───────────────┘
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │ Phase 6: PIPELINE TESTING    │
                   │ pytest Unit & Data Tests     │
                   │  182 tests | 2.40s runtime   │
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

### 🔹 PHASE 5: Gold Layer — Star Schema Analytical Modeling
- **Goal**: Transform the Silver conformed data into a full analytical star schema (Gold Layer) — the final tier of the Medallion Architecture, optimised for BI tools, dashboards, and data science consumption.
- **What We Built**:
  - `src/models_gold.py`: Four SQLAlchemy ORM models forming the star schema:
    - `DimPatient` — Patient dimension (patient_key, patient_id, age, gender, country)
    - `DimTrial` — Clinical trial dimension (trial_key, trial_id, treatment, dates, duration)
    - `DimDrug` — Drug dimension (drug_key, drug_id, drug_name)
    - `FactClinicalOutcomes` — Central fact table with FK references to all dimensions, numeric measures (dosage, treatment_duration_days), and derived analytical flags (outcome_binary, outcome_category)
  - `src/build_gold.py`: End-to-end Gold layer pipeline:
    - Reads from `silver_clinical_trials` table
    - Builds and loads all 4 dimension and fact tables
    - Resolves surrogate foreign keys via Pandas merge (equivalent to SQL JOIN)
    - Derives `outcome_binary` (1/0) and `outcome_category` (Positive/Negative/Neutral) for analytics
    - Exports all Gold tables as Parquet files under `data/gold/`
    - Prints analytical summary: success rates, top countries, drug performance

---

### 🔹 PHASE 6: Pipeline Testing — pytest Unit & Data Quality Tests
- **Goal**: Build a comprehensive automated test suite that validates every critical piece of the pipeline works correctly — without touching the database. Industry-standard practice before deploying any data pipeline.
- **What We Built**:
  - `tests/conftest.py`: Shared pytest fixtures (sample records, Silver DataFrame) available to all test files automatically
  - `tests/test_validation.py`: 80+ tests for the data validation engine (Phase 3):
    - Valid record acceptance (no false positives)
    - Age boundary conditions (18–100), numeric type casting
    - Dosage range validation (0–500mg), malformed value rejection
    - Mandatory field null checks (parametrized over all 6 fields)
    - Date format validation, chronological order enforcement
    - Categorical standardization — gender & country mapping (parametrized, 25+ variants)
    - Full batch of invalid records all rejected
  - `tests/test_build_gold.py`: 50+ tests for Gold layer helper functions (Phase 5):
    - `_derive_outcome_binary`: all positive/negative outcomes, case-insensitivity, None/empty edge cases
    - `_derive_outcome_category`: Positive/Negative/Neutral mapping, all categories valid
    - `_derive_drug_name`: known DRUG-N IDs, legacy D-00x IDs, unknown fallback, whitespace stripping
    - DataFrame-level integration tests: deduplication counts, column creation, fact row count
  - `tests/test_config.py`: 25+ project structure & configuration tests:
    - Config class attributes, URI format validation, Path object types
    - Required columns completeness, no duplicates
    - All critical source files and directories exist on disk
  - `tests/test_data_ingestion.py`: Raw data file integrity tests (Phase 1 output):
    - File existence, non-empty, correct extension
    - Schema: all required columns present, no unnamed headers
    - Row count in expected range (900–1200)
    - patient_id format, anomaly presence confirmation
  - `src/run_tests.py`: Convenience script to execute full test suite
  - `pytest.ini`: pytest configuration (test discovery, verbosity, log level)
- **Results**: **182 tests, 0 failures, completed in 2.40 seconds**

---


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
│   ├── gold/
│   │   ├── dim_patient.parquet           # Patient dimension
│   │   ├── dim_trial.parquet             # Trial dimension
│   │   ├── dim_drug.parquet              # Drug dimension
│   │   └── fact_clinical_outcomes.parquet # Central fact table
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
│   ├── models_gold.py          # SQLAlchemy Gold layer ORM models (star schema)
│   ├── run_sql_analytics.py    # SQL analytics execution engine
│   ├── run_tests.py            # Phase 6 test suite runner
│   ├── spark_silver.py         # PySpark Silver Transformation Engine
│   ├── build_gold.py           # Gold Layer Star Schema Build Pipeline
│   └── validation.py           # Data Quality Rules & Quarantine Engine
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Shared pytest fixtures
│   ├── test_validation.py      # Phase 3: Validation engine tests (80+ tests)
│   ├── test_build_gold.py      # Phase 5: Gold layer function tests (50+ tests)
│   ├── test_config.py          # Config & project structure tests (25+ tests)
│   └── test_data_ingestion.py  # Raw data ingestion tests (25+ tests)
├── pytest.ini                  # pytest configuration
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

7. **Build Gold Layer Star Schema (Phase 5)**:
   ```powershell
   python src/build_gold.py
   ```

8. **Run Full Pipeline Test Suite (Phase 6)**:
   ```powershell
   python src/run_tests.py
   ```
   Or run pytest directly:
   ```powershell
   pytest tests/ -v
   pytest tests/test_validation.py -v        # validation tests only
   pytest tests/test_build_gold.py -v        # gold layer tests only
   pytest tests/ -v -k "TestAgeValidation"   # run one test class
   ```

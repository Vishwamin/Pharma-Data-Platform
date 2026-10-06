# Enterprise Pharma Clinical Data Engineering Pipeline

An end-to-end Medallion-Architecture Data Pipeline built for Clinical Trial Analytics.

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
- **Why We Did It**:
  - Prevents hardcoded local paths and database credentials.
  - Ensures raw file integrity is audited before downstream data transformations run.
  - Preserves exact source strings to prevent silent data corruption during ingestion.

---

### 🔹 PHASE 2: Database Layer & Bronze Storage Landing
- **Goal**: Establish the raw database storage layer (Bronze Layer) using SQLAlchemy with PostgreSQL / local database fallback.
- **What We Built**:
  - `src/database.py`: SQLAlchemy engine management, session pooling, health checks, and database fallback handler.
  - `src/models_bronze.py`: `BronzeClinicalTrials` ORM table schema preserving raw string data and audit metadata (`ingestion_timestamp`, `source_file_name`).
  - `src/load_bronze.py`: Ingestion pipeline loading raw CSV string payloads into the Bronze database table in batch chunks.
- **Why We Did It**:
  - The Bronze layer serves as an immutable raw landing zone preserving full data lineage.
  - Storing fields as strings in Bronze ensures dirty records land successfully without throwing database level type-casting errors.
  - Provides a surrogate primary key (`raw_id`) so every raw record is uniquely addressable regardless of natural key quality.

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
│   └── pharma_clinical_db.db        # Local database storage
├── logs/
│   └── pipeline.log            # Persistent audit logs
├── src/
│   ├── __init__.py
│   ├── database.py             # SQLAlchemy DB engine & connection manager
│   ├── generate_synthetic_data.py  # Synthetic clinical data generator
│   ├── ingest.py               # Raw file ingestion module
│   ├── load_bronze.py          # Bronze pipeline loader
│   ├── logger.py               # Production logging utility
│   └── models_bronze.py        # SQLAlchemy Bronze layer ORM model
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

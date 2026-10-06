# Enterprise Pharma Clinical Data Engineering Pipeline

An end-to-end Medallion-Architecture Data Pipeline built for Clinical Trial Analytics.

## Pipeline Architecture Overview
```
[ Raw CSV Files / Data Lake ]
             │
             ▼ (Phase 1: Ingestion & Config)
     Python Ingest & Logging
             │
             ▼ (Phase 2: Raw Storage)
      PostgreSQL Bronze Layer
             │
             ▼ (Phase 3 & 4: Processing & Validation)
  PySpark Quality & Cleaning (Silver)
             │
             ▼ (Phase 5: Analytics Modeling)
  Gold Star-Schema Analytical Marts
```

## Directory Structure
```
pharma-data-pipeline/
├── config/
│   ├── __init__.py
│   └── config.py               # Central configuration & ENV loading
├── data/
│   └── raw/                    # Raw land zone for landed files
├── logs/
│   └── pipeline.log            # Audit trailing and execution logs
├── src/
│   ├── __init__.py
│   ├── generate_synthetic_data.py  # Realistic data generator with anomalies
│   ├── logger.py               # Production logging utility
│   └── ingest.py               # Raw ingestion module
├── tests/                      # Unit & pipeline test suites
├── .env.example                # Template environment variables
├── .gitignore
├── README.md
└── requirements.txt            # Python dependencies
```

## Getting Started (Phase 1)
1. Install Python 3.10+
2. Install requirements: `pip install -r requirements.txt`
3. Generate synthetic data: `python src/generate_synthetic_data.py`
4. Run raw ingestion: `python src/ingest.py`

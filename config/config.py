import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory of the Project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file if it exists
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

class Config:
    """Central configuration management for the Data Pipeline."""
    ENV = os.getenv("ENV", "development")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Absolute paths for data & logging directories
    RAW_DATA_PATH = BASE_DIR / os.getenv("RAW_DATA_PATH", "data/raw/clinical_trials_raw.csv")
    LOG_FILE_PATH = BASE_DIR / os.getenv("LOG_FILE_PATH", "logs/pipeline.log")
    
    # Ensure directories exist
    RAW_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Database Configuration (PostgreSQL with SQLite fallback)
    POSTGRES_USER = os.getenv("POSTGRES_USER", "pharma_admin")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "pharma_pass")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "pharma_clinical_db")

    # Primary Database URI (explicitly using psycopg2 driver)
    POSTGRES_URI = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    
    # Local SQLite Fallback URI (for offline development without active PostgreSQL server)
    SQLITE_URI = f"sqlite:///{BASE_DIR / 'data' / 'pharma_clinical_db.db'}"

    # Required raw data schema columns for ingestion verification
    REQUIRED_COLUMNS = [
        "patient_id",
        "trial_id",
        "drug_id",
        "age",
        "gender",
        "country",
        "treatment",
        "dosage",
        "start_date",
        "end_date",
        "outcome"
    ]

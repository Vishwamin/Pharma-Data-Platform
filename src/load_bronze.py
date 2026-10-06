import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import text

# Ensure project root is in Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.config import Config
from src.logger import get_logger
from src.database import engine, Base
from src.models_bronze import BronzeClinicalTrials
from src.ingest import ingest_raw_csv

logger = get_logger("BronzeDataLoader")

def create_bronze_tables():
    """Creates the Bronze tables in the target database if they do not exist."""
    logger.info("Verifying Bronze layer table schemas in target database...")
    Base.metadata.create_all(bind=engine)
    logger.info("Bronze layer tables verified/created successfully.")

def load_raw_to_bronze(file_path: Path = None) -> int:
    """
    Phase 2 Bronze Pipeline:
    1. Ingests raw string CSV data using ingest_raw_csv().
    2. Ensures Bronze tables exist.
    3. Appends raw data into 'bronze_clinical_trials' table.
    4. Audits total record count in Bronze layer.
    """
    logger.info("--- Starting Phase 2: Loading Raw Data into Bronze Database Layer ---")

    # Step 1: Ingest raw CSV as string DataFrame
    df_raw = ingest_raw_csv(file_path)

    # Step 2: Add Ingestion Metadata columns
    source_name = file_path.name if file_path else Config.RAW_DATA_PATH.name
    df_raw["source_file_name"] = source_name
    # ingestion_timestamp will automatically be assigned by database default,
    # or we can let the database apply CURRENT_TIMESTAMP.

    # Step 3: Create schema tables if not existing
    create_bronze_tables()

    # Step 4: Load into database table using SQLAlchemy engine
    logger.info(f"Appending {len(df_raw)} records to table '{BronzeClinicalTrials.__tablename__}'...")
    
    try:
        # Load raw data into database table
        df_raw.to_sql(
            name=BronzeClinicalTrials.__tablename__,
            con=engine,
            if_exists="append",
            index=False,
            chunksize=500  # Load in batches of 500 rows
        )
        logger.info("Successfully loaded raw records into Bronze table.")
    except Exception as e:
        logger.error(f"Failed to load records into Bronze table: {str(e)}")
        raise e

    # Step 5: Verify record count in Bronze table
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {BronzeClinicalTrials.__tablename__}"))
        total_bronze_count = result.scalar()

    logger.info(f"Bronze Layer Database Audit: Total records in table = {total_bronze_count}")
    return total_bronze_count

if __name__ == "__main__":
    count = load_raw_to_bronze()
    print(f"\n--- Phase 2 Complete: Bronze Table Total Record Count = {count} ---")

import os
import pandas as pd
from pathlib import Path
import sys

# Ensure root directory is in python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.config import Config
from src.logger import get_logger

logger = get_logger("RawDataIngestion")

def ingest_raw_csv(file_path: Path = None) -> pd.DataFrame:
    """
    Phase 1 Ingestion:
    Reads raw CSV data from storage, validates file presence & structural schema,
    and returns an unparsed raw pandas DataFrame.
    """
    if file_path is None:
        file_path = Config.RAW_DATA_PATH

    logger.info(f"Starting raw data ingestion from: {file_path}")

    # 1. File existence check
    if not os.path.exists(file_path):
        error_msg = f"Ingestion Error: File not found at path '{file_path}'"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    # 2. Inspect File Size
    file_size_bytes = os.path.getsize(file_path)
    file_size_kb = file_size_bytes / 1024.0
    logger.info(f"Raw file size: {file_size_kb:.2f} KB ({file_size_bytes} bytes)")

    # 3. Load CSV as raw strings to avoid early datatype coercion errors
    try:
        df_raw = pd.read_csv(file_path, dtype=str)
        logger.info(f"Successfully loaded CSV into pandas DataFrame. Shape: {df_raw.shape}")
    except Exception as e:
        logger.error(f"Failed to parse CSV file: {str(e)}")
        raise e

    # 4. Schema structural check (Ensure all required columns exist)
    missing_cols = [col for col in Config.REQUIRED_COLUMNS if col not in df_raw.columns]
    if missing_cols:
        error_msg = f"Ingestion Error: Structural schema mismatch. Missing required columns: {missing_cols}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info("Schema structural verification passed: All required columns present.")
    
    # 5. Output raw summary stats for audit logging
    total_records = len(df_raw)
    null_counts = df_raw.isnull().sum().to_dict()
    logger.info(f"Raw record count: {total_records}")
    logger.debug(f"Raw null value breakdown across columns: {null_counts}")

    return df_raw

if __name__ == "__main__":
    df = ingest_raw_csv()
    print("\n--- Raw Data Preview (First 5 Rows) ---")
    print(df.head())

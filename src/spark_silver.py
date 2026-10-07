import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

# Ensure project root is in Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.config import Config, BASE_DIR
from src.logger import get_logger
from src.database import engine, Base
from src.models_silver import SilverClinicalTrials
from src.validation import run_data_validation_pipeline

logger = get_logger("PySparkSilverPipeline")

def process_bronze_to_silver() -> int:
    """
    Phase 4 Pipeline: PySpark Transformation & Silver Layer Conformed Landing Zone.
    
    Processes validated clean records, enforces Silver schema datatypes, 
    calculates derived features (treatment_duration_days), applies window deduplication,
    loads the database 'silver_clinical_trials' table, and writes partitioned Parquet data lake files.
    """
    logger.info("--- Starting Phase 4: PySpark Transformation to Silver Layer ---")
    
    # Ensure Silver DB schema exists in PostgreSQL / Database
    Base.metadata.create_all(bind=engine)

    # 1. Fetch validated clean records from Phase 3 validation engine
    df_clean_pd, _, metrics = run_data_validation_pipeline()
    
    if df_clean_pd.empty:
        logger.warning("No clean records returned from validation engine. Silver pipeline aborted.")
        return 0

    logger.info(f"Loaded {len(df_clean_pd)} validated records for Silver transformation.")

    # 2. Attempt PySpark Session Execution
    spark_success = False
    silver_df_spark = None

    try:
        from pyspark.sql import SparkSession
        from pyspark.sql import functions as F
        from pyspark.sql.types import IntegerType, DoubleType, DateType
        from pyspark.sql.window import Window

        logger.info("Initializing PySpark SparkSession...")
        spark = SparkSession.builder \
            .appName("Pharma-Silver-Pipeline") \
            .master("local[*]") \
            .config("spark.driver.memory", "2g") \
            .getOrCreate()
        spark.sparkContext.setLogLevel("WARN")

        # Convert Pandas DataFrame to PySpark DataFrame
        df_clean_pd_clean = df_clean_pd.where(pd.notnull(df_clean_pd), None)
        spark_raw = spark.createDataFrame(df_clean_pd_clean.astype(str))

        # PySpark Schema Transformations
        silver_spark = spark_raw \
            .withColumn("age", F.col("age").cast(IntegerType())) \
            .withColumn("dosage", F.col("dosage").cast(DoubleType())) \
            .withColumn("start_date", F.to_date(F.col("start_date"), "yyyy-MM-dd")) \
            .withColumn("end_date", F.to_date(F.col("end_date"), "yyyy-MM-dd")) \
            .withColumn("treatment_duration_days", F.datediff(F.col("end_date"), F.col("start_date"))) \
            .withColumn("processed_at", F.current_timestamp())

        # PySpark Window Function Deduplication
        window_spec = Window.partitionBy("patient_id", "trial_id").orderBy(F.col("start_date").asc())
        silver_spark_dedup = silver_spark \
            .withColumn("row_num", F.row_number().over(window_spec)) \
            .filter(F.col("row_num") == 1) \
            .drop("row_num")

        pdf_silver = silver_spark_dedup.toPandas()
        spark.stop()
        spark_success = True
        logger.info("PySpark native JVM transformation completed successfully.")

    except Exception as py_err:
        logger.warning(f"PySpark JVM runtime notice ({str(py_err).splitlines()[0]}). Executing PySpark DataFrame transformation engine via Pandas/Parquet fallback...")
        
        # PySpark Transformation Engine Logic via Pandas/PyArrow
        pdf_silver = df_clean_pd.copy()
        
        # Datatype Enforcement (Integer, Float, Date)
        pdf_silver["age"] = pd.to_numeric(pdf_silver["age"], errors="coerce").astype(int)
        pdf_silver["dosage"] = pd.to_numeric(pdf_silver["dosage"], errors="coerce").astype(float)
        pdf_silver["start_date"] = pd.to_datetime(pdf_silver["start_date"], format="%Y-%m-%d").dt.date
        pdf_silver["end_date"] = pd.to_datetime(pdf_silver["end_date"], format="%Y-%m-%d").dt.date
        
        # Derived Feature: treatment_duration_days
        start_dates = pd.to_datetime(pdf_silver["start_date"])
        end_dates = pd.to_datetime(pdf_silver["end_date"])
        pdf_silver["treatment_duration_days"] = (end_dates - start_dates).dt.days
        
        # Window Function Deduplication
        pdf_silver = pdf_silver.sort_values("start_date").groupby(["patient_id", "trial_id"]).first().reset_index()

    # 3. Select Target Silver Schema Columns
    target_cols = [
        "patient_id", "trial_id", "drug_id", "age", "gender", "country",
        "treatment", "dosage", "start_date", "end_date", "outcome", "treatment_duration_days"
    ]
    
    pdf_silver_db = pdf_silver[target_cols].copy()

    # 4. Truncate & Load into Database Silver Table ('silver_clinical_trials')
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text(f"DELETE FROM {SilverClinicalTrials.__tablename__}"))
        conn.commit()

    pdf_silver_db.to_sql(
        name=SilverClinicalTrials.__tablename__,
        con=engine,
        if_exists="append",
        index=False,
        chunksize=500
    )
    
    silver_record_count = len(pdf_silver_db)
    logger.info(f"Silver Layer Database Audit: Loaded {silver_record_count} conformed records into table '{SilverClinicalTrials.__tablename__}'.")

    # 5. Export Partitioned Parquet Data Lake Storage
    parquet_output_dir = BASE_DIR / "data" / "silver" / "clinical_trials_parquet"
    parquet_output_dir.mkdir(parents=True, exist_ok=True)

    # Save as partitioned parquet files by trial_id
    try:
        pdf_silver_db.to_parquet(
            path=str(parquet_output_dir),
            partition_cols=["trial_id"],
            index=False,
            engine="pyarrow"
        )
        logger.info(f"Silver Data Lake Export: Saved partitioned Parquet files at: {parquet_output_dir}")
    except Exception as p_err:
        # Fallback if pyarrow is missing
        pdf_silver_db.to_csv(BASE_DIR / "data" / "silver" / "clinical_trials_silver.csv", index=False)
        logger.info("Saved Silver layer output to CSV file.")

    return silver_record_count

if __name__ == "__main__":
    count = process_bronze_to_silver()
    print(f"\n--- Phase 4 Complete: Total Silver Layer Conformed Records = {count} ---")

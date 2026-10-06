import csv
import random
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Ensure project root is in python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.config import Config
from src.logger import get_logger

logger = get_logger("GenerateSyntheticData")

COUNTRIES = ["USA", "Germany", "Japan", "UK", "Canada", "France", "US", "UNITED STATES"]
TREATMENTS = ["Drug_A_10mg", "Drug_A_20mg", "Placebo", "Drug_B_50mg", "drug_a_10mg", "N/A", None]
GENDERS_CLEAN_DIRTY = ["Male", "Female", "M", "F", "MALE", "FEMALE", "Unknown", None]
OUTCOMES = ["Completed", "Withdrawn", "Adverse Event", "Effective", "Non-Responsive", "completed", None]

def generate_clinical_trial_data(num_rows: int = 1000, seed: int = 42) -> Path:
    """
    Generates synthetic clinical trial data containing both valid records
    and intentional data-quality anomalies to test validation pipelines.
    """
    random.seed(seed)
    output_path = Config.RAW_DATA_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting synthetic dataset generation ({num_rows} records)...")

    base_start_date = datetime(2023, 1, 1)

    records = []
    
    for i in range(1, num_rows + 1):
        patient_id = f"P{1000 + i}"
        trial_id = f"CT-{random.randint(101, 105)}"
        drug_id = f"DRUG-{random.randint(1, 4)}"

        # 1. Normal clean values by default
        age = random.randint(18, 85)
        gender = random.choice(["Male", "Female"])
        country = random.choice(["USA", "Germany", "Japan", "UK"])
        treatment = random.choice(["Drug_A_10mg", "Placebo", "Drug_B_50mg"])
        dosage = float(random.choice([10, 20, 50, 100]))
        
        start_dt = base_start_date + timedelta(days=random.randint(0, 300))
        end_dt = start_dt + timedelta(days=random.randint(30, 180))
        start_date = start_dt.strftime("%Y-%m-%d")
        end_date = end_dt.strftime("%Y-%m-%d")
        
        outcome = random.choice(["Completed", "Withdrawn", "Adverse Event", "Effective"])

        # Inject intentional dirty/bad data (approx 15-20% rate across types)
        rand_anomaly = random.random()

        if rand_anomaly < 0.03:
            # Anomaly 1: Invalid Age (-5 or 190 or None)
            age = random.choice([-5, 190, None, "ninety"])
            logger.debug(f"Injected invalid age for patient {patient_id}: {age}")

        elif rand_anomaly < 0.06:
            # Anomaly 2: Null / Missing values in critical fields
            treatment = None
            outcome = None
            logger.debug(f"Injected null treatment/outcome for patient {patient_id}")

        elif rand_anomaly < 0.09:
            # Anomaly 3: Invalid Date ordering (end_date before start_date) or malformed string
            end_date = (start_dt - timedelta(days=20)).strftime("%Y-%m-%d")
            logger.debug(f"Injected end_date before start_date for patient {patient_id}")

        elif rand_anomaly < 0.12:
            # Anomaly 4: Inconsistent categorical casing / abbreviations
            gender = random.choice(["M", "F", "MALE", "FEMALE", "m", "f"])
            country = random.choice(["US", "UNITED STATES", "germany", "JAPAN"])
            logger.debug(f"Injected inconsistent categorical values for patient {patient_id}")

        elif rand_anomaly < 0.15:
            # Anomaly 5: Negative or Malformed dosage
            dosage = random.choice([-50.0, "INVALID_DOSAGE", 99999.0])
            logger.debug(f"Injected invalid dosage for patient {patient_id}: {dosage}")

        record = {
            "patient_id": patient_id,
            "trial_id": trial_id,
            "drug_id": drug_id,
            "age": age,
            "gender": gender,
            "country": country,
            "treatment": treatment,
            "dosage": dosage,
            "start_date": start_date,
            "end_date": end_date,
            "outcome": outcome
        }
        records.append(record)

    # Inject explicit exact duplicate records (Anomaly 6: Duplicates)
    num_duplicates = int(num_rows * 0.03)  # ~3% duplicates
    logger.info(f"Injecting {num_duplicates} exact duplicate records...")
    for _ in range(num_duplicates):
        dup_record = random.choice(records[:100]).copy()
        records.append(dup_record)

    # Write to CSV
    fieldnames = Config.REQUIRED_COLUMNS
    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    logger.info(f"Successfully generated synthetic dataset at: {output_path} (Total rows: {len(records)})")
    return output_path

if __name__ == "__main__":
    generate_clinical_trial_data(num_rows=1000)

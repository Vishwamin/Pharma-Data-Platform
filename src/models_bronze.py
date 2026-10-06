from sqlalchemy import Column, Integer, String, DateTime, func
from src.database import Base

class BronzeClinicalTrials(Base):
    """
    SQLAlchemy ORM Model representing the BRONZE raw database table.
    
    The Bronze layer acts as an immutable landing zone.
    All data fields are intentionally kept as raw VARCHAR/Strings to preserve 
    source data anomalies for auditing and data-quality engineering in downstream layers.
    """
    __tablename__ = "bronze_clinical_trials"

    # Primary Key / Surrogate Key for raw records
    raw_id = Column(Integer, primary_key=True, autoincrement=True, comment="Surrogate Primary Key")
    
    # Raw source payload fields
    patient_id = Column(String(50), nullable=True)
    trial_id = Column(String(50), nullable=True)
    drug_id = Column(String(50), nullable=True)
    age = Column(String(50), nullable=True)  # Raw string to preserve corrupted values (-5, "ninety", null)
    gender = Column(String(50), nullable=True)
    country = Column(String(50), nullable=True)
    treatment = Column(String(100), nullable=True)
    dosage = Column(String(50), nullable=True)  # Raw string to preserve invalid dosage values
    start_date = Column(String(50), nullable=True)
    end_date = Column(String(50), nullable=True)
    outcome = Column(String(100), nullable=True)

    # Ingestion Audit Metadata
    ingestion_timestamp = Column(DateTime, server_default=func.now(), nullable=False)
    source_file_name = Column(String(255), default="clinical_trials_raw.csv", nullable=False)

    def __repr__(self):
        return f"<BronzeClinicalTrials(raw_id={self.raw_id}, patient_id='{self.patient_id}', trial_id='{self.trial_id}')>"

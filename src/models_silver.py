from sqlalchemy import Column, Integer, String, Date, Float, DateTime, func
from src.database import Base

class SilverClinicalTrials(Base):
    """
    SQLAlchemy ORM Model representing the SILVER cleansed & conformed layer.
    
    The Silver layer in Medallion Architecture holds cleansed, deduplicated, 
    and strongly-typed data (proper Integers, Floats, and SQL Dates).
    """
    __tablename__ = "silver_clinical_trials"

    silver_id = Column(Integer, primary_key=True, autoincrement=True, comment="Surrogate Primary Key")
    patient_id = Column(String(50), nullable=False, index=True)
    trial_id = Column(String(50), nullable=False, index=True)
    drug_id = Column(String(50), nullable=False)
    age = Column(Integer, nullable=False)  # Enforced integer datatype
    gender = Column(String(20), nullable=False)  # Standardized ('Male', 'Female')
    country = Column(String(50), nullable=False)  # Standardized ('USA', 'Germany', etc.)
    treatment = Column(String(100), nullable=False)
    dosage = Column(Float, nullable=False)  # Enforced float numeric type
    start_date = Column(Date, nullable=False)  # Enforced ISO Date type
    end_date = Column(Date, nullable=True)  # Enforced ISO Date type
    outcome = Column(String(100), nullable=False)
    
    # Derived Feature Engineering Columns created in PySpark
    treatment_duration_days = Column(Integer, nullable=True, comment="Calculated in PySpark: end_date - start_date")
    processed_at = Column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<SilverClinicalTrials(silver_id={self.silver_id}, patient_id='{self.patient_id}', trial_id='{self.trial_id}')>"

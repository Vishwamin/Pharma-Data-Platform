from sqlalchemy import Column, Integer, String, DateTime, Text, func
from src.database import Base

class QuarantineClinicalTrials(Base):
    """
    SQLAlchemy ORM Model representing Quarantined (Corrupted/Invalid) Data.
    
    In enterprise pipelines, dirty or invalid records are never silently dropped or ignored.
    Instead, they are isolated in a Quarantine table with exact failure reasons for 
    audit logging, compliance reporting, and root-cause remediation.
    """
    __tablename__ = "quarantine_clinical_trials"

    quarantine_id = Column(Integer, primary_key=True, autoincrement=True, comment="Quarantine Record ID")
    raw_id = Column(Integer, nullable=True, comment="Reference to raw_id in Bronze table")
    patient_id = Column(String(50), nullable=True)
    trial_id = Column(String(50), nullable=True)
    drug_id = Column(String(50), nullable=True)
    age = Column(String(50), nullable=True)
    gender = Column(String(50), nullable=True)
    country = Column(String(50), nullable=True)
    treatment = Column(String(100), nullable=True)
    dosage = Column(String(50), nullable=True)
    start_date = Column(String(50), nullable=True)
    end_date = Column(String(50), nullable=True)
    outcome = Column(String(100), nullable=True)

    # Quarantine Failure Audit Metadata
    violation_reasons = Column(Text, nullable=False, comment="Comma-separated or JSON list of data quality rule failures")
    quarantined_at = Column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<QuarantineClinicalTrials(quarantine_id={self.quarantine_id}, raw_id={self.raw_id}, reasons='{self.violation_reasons}')>"

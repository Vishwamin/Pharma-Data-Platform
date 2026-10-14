from sqlalchemy import Column, Integer, String, Date, Float, DateTime, ForeignKey, func
from src.database import Base


class DimPatient(Base):
    """
    GOLD Layer — Patient Dimension Table (SCD Type 1).

    Stores one unique record per patient with their latest demographic attributes.
    In a Star Schema, dimension tables describe the 'who' — here, the patient.

    SCD Type 1 means we simply overwrite old data when patient details change
    (no history tracking). For history tracking, SCD Type 2 would add effective_date
    and expiry_date columns.
    """
    __tablename__ = "dim_patient"

    # Surrogate Key — system-generated integer, used as the FK in the fact table
    patient_key = Column(Integer, primary_key=True, autoincrement=True,
                         comment="Surrogate PK — used as FK in fact table")

    # Business / Natural Key — the real-world identifier from source systems
    patient_id  = Column(String(50), nullable=False, unique=True, index=True,
                         comment="Natural Key — source system patient identifier")

    # Patient Demographic Attributes
    age     = Column(Integer, nullable=False)
    gender  = Column(String(20), nullable=False)
    country = Column(String(50), nullable=False)

    # Audit
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self):
        return (f"<DimPatient(patient_key={self.patient_key}, "
                f"patient_id='{self.patient_id}', country='{self.country}')>")


class DimTrial(Base):
    """
    GOLD Layer — Clinical Trial Dimension Table.

    Stores one unique record per clinical trial with its descriptive attributes.
    Describes the 'what' context of each trial — treatment used, dates, duration.
    """
    __tablename__ = "dim_trial"

    # Surrogate Key
    trial_key = Column(Integer, primary_key=True, autoincrement=True,
                       comment="Surrogate PK — used as FK in fact table")

    # Business / Natural Key
    trial_id = Column(String(50), nullable=False, unique=True, index=True,
                      comment="Natural Key — source system trial identifier")

    # Trial Descriptive Attributes
    treatment               = Column(String(100), nullable=False)
    start_date              = Column(Date, nullable=False)
    end_date                = Column(Date, nullable=True)
    treatment_duration_days = Column(Integer, nullable=True,
                                     comment="Derived: end_date - start_date in days")

    # Audit
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self):
        return (f"<DimTrial(trial_key={self.trial_key}, "
                f"trial_id='{self.trial_id}', treatment='{self.treatment}')>")


class DimDrug(Base):
    """
    GOLD Layer — Drug Dimension Table.

    Stores one unique record per drug used across clinical trials.
    Describes the 'which drug' context — current and future versions
    could include dosage form, drug class, mechanism of action, etc.
    """
    __tablename__ = "dim_drug"

    # Surrogate Key
    drug_key = Column(Integer, primary_key=True, autoincrement=True,
                      comment="Surrogate PK — used as FK in fact table")

    # Business / Natural Key
    drug_id   = Column(String(50), nullable=False, unique=True, index=True,
                       comment="Natural Key — source system drug identifier")

    # Drug Descriptive Attributes
    drug_name = Column(String(100), nullable=False,
                       comment="Human-readable drug name derived from drug_id")

    # Audit
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self):
        return (f"<DimDrug(drug_key={self.drug_key}, "
                f"drug_id='{self.drug_id}', drug_name='{self.drug_name}')>")


class FactClinicalOutcomes(Base):
    """
    GOLD Layer — Clinical Outcomes Fact Table (Central Fact Table).

    The heart of the Star Schema. Stores one measurable event per patient-trial
    combination with foreign keys pointing to all dimension tables.

    Fact tables store:
      - Foreign Keys to every dimension (who, what, which drug)
      - Numeric Measures (dosage, treatment_duration_days)
      - Derived Analytical Flags (outcome_binary, outcome_category)

    This table is what BI tools (Tableau, Power BI, Looker) query directly.
    """
    __tablename__ = "fact_clinical_outcomes"

    # Surrogate Primary Key for the fact record
    fact_id = Column(Integer, primary_key=True, autoincrement=True,
                     comment="Surrogate PK for this fact row")

    # ── Foreign Keys to Dimension Tables ──────────────────────────────────────
    patient_key = Column(Integer, ForeignKey("dim_patient.patient_key"),
                         nullable=False, index=True,
                         comment="FK → dim_patient")
    trial_key   = Column(Integer, ForeignKey("dim_trial.trial_key"),
                         nullable=False, index=True,
                         comment="FK → dim_trial")
    drug_key    = Column(Integer, ForeignKey("dim_drug.drug_key"),
                         nullable=False, index=True,
                         comment="FK → dim_drug")

    # ── Denormalized Business Keys (for easier querying without joins) ─────────
    patient_id = Column(String(50), nullable=False)
    trial_id   = Column(String(50), nullable=False)
    drug_id    = Column(String(50), nullable=False)

    # ── Measures (Numeric Facts) ───────────────────────────────────────────────
    dosage                  = Column(Float, nullable=False,
                                     comment="Drug dosage in mg")
    treatment_duration_days = Column(Integer, nullable=True,
                                     comment="Days from start_date to end_date")

    # ── Outcome Fields ─────────────────────────────────────────────────────────
    outcome          = Column(String(100), nullable=False,
                              comment="Raw outcome string: Recovered, Worsened, etc.")
    outcome_binary   = Column(Integer, nullable=False,
                              comment="Derived: 1 = Positive outcome, 0 = Negative")
    outcome_category = Column(String(50), nullable=False,
                              comment="Derived: Positive / Negative / Neutral")

    # ── Audit ──────────────────────────────────────────────────────────────────
    processed_at = Column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self):
        return (f"<FactClinicalOutcomes(fact_id={self.fact_id}, "
                f"patient_id='{self.patient_id}', trial_id='{self.trial_id}', "
                f"outcome='{self.outcome}')>")

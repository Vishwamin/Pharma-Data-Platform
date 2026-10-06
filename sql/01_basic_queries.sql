-- ============================================================================
-- SQL MODULE 1: Basics (SELECT, WHERE, ORDER BY, DISTINCT)
-- Database: pharma_clinical_db
-- Table: bronze_clinical_trials
-- ============================================================================

-- 1. Simple SELECT with filtering (WHERE) and sorting (ORDER BY)
-- Business Goal: Retrieve all clinical trial records for 'Drug_A_10mg' ordered by patient_id
SELECT 
    raw_id,
    patient_id,
    trial_id,
    drug_id,
    age,
    treatment,
    dosage,
    start_date,
    end_date,
    outcome
FROM bronze_clinical_trials
WHERE treatment = 'Drug_A_10mg'
ORDER BY patient_id ASC
LIMIT 10;

-- 2. Finding UNIQUE values across categorical columns (DISTINCT)
-- Business Goal: Identify all unique countries represented in raw clinical trials
SELECT DISTINCT 
    country 
FROM bronze_clinical_trials
WHERE country IS NOT NULL
ORDER BY country;

-- 3. Multi-condition filtering using AND, OR, IN
-- Business Goal: Identify patients enrolled in trials CT-101 or CT-102 with non-null outcome
SELECT 
    patient_id,
    trial_id,
    drug_id,
    treatment,
    outcome
FROM bronze_clinical_trials
WHERE trial_id IN ('CT-101', 'CT-102')
  AND outcome IS NOT NULL
ORDER BY trial_id, patient_id;

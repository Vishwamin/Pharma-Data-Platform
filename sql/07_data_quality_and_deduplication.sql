-- ============================================================================
-- SQL MODULE 7: Data Quality Profiling & NULL Handling
-- Database: pharma_clinical_db
-- ============================================================================

-- 1. Auditing NULL rates across all columns in Bronze landing layer
-- Business Goal: Calculate exact percentage of missing values per column
SELECT 
    COUNT(*) AS total_records,
    ROUND(100.0 * COUNT(*) FILTER (WHERE patient_id IS NULL) / COUNT(*), 2) AS null_pct_patient_id,
    ROUND(100.0 * COUNT(*) FILTER (WHERE age IS NULL OR age = '') / COUNT(*), 2) AS null_pct_age,
    ROUND(100.0 * COUNT(*) FILTER (WHERE treatment IS NULL OR treatment = 'N/A') / COUNT(*), 2) AS null_pct_treatment,
    ROUND(100.0 * COUNT(*) FILTER (WHERE dosage IS NULL) / COUNT(*), 2) AS null_pct_dosage,
    ROUND(100.0 * COUNT(*) FILTER (WHERE outcome IS NULL) / COUNT(*), 2) AS null_pct_outcome
FROM bronze_clinical_trials;

-- 2. COALESCE and NULLIF for Default Fallback Handling
-- Business Goal: Replace NULL outcome values with 'Pending Follow-up' and convert 'N/A' strings to true NULLs
SELECT 
    patient_id,
    treatment,
    COALESCE(outcome, 'Pending Follow-up') AS cleansed_outcome,
    NULLIF(TRIM(treatment), 'N/A') AS nullified_treatment
FROM bronze_clinical_trials
WHERE outcome IS NULL OR treatment = 'N/A'
LIMIT 10;

-- 3. Duplicate Detection Query
-- Business Goal: Identify exact patient_id + trial_id business duplicates
SELECT 
    patient_id,
    trial_id,
    COUNT(*) AS duplicate_count,
    ARRAY_AGG(raw_id) AS conflicting_raw_ids
FROM bronze_clinical_trials
GROUP BY patient_id, trial_id
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC
LIMIT 10;

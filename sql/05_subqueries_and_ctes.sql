-- ============================================================================
-- SQL MODULE 5: Subqueries & Common Table Expressions (CTEs)
-- Database: pharma_clinical_db
-- ============================================================================

-- 1. Scalar Subquery in WHERE clause
-- Business Goal: Identify patients taking a dosage above the overall dataset average
SELECT 
    patient_id,
    trial_id,
    treatment,
    CAST(dosage AS NUMERIC) AS dosage_mg
FROM bronze_clinical_trials
WHERE dosage ~ '^[0-9]+(\.[0-9]+)?$'
  AND CAST(dosage AS NUMERIC) > (
      SELECT AVG(CAST(dosage AS NUMERIC))
      FROM bronze_clinical_trials
      WHERE dosage ~ '^[0-9]+(\.[0-9]+)?$'
  )
ORDER BY dosage_mg DESC
LIMIT 10;

-- 2. CTE (Common Table Expression) for Multi-Step Data Quality Breakdown
-- Business Goal: Calculate pass/fail percentages per clinical trial using a clean CTE
WITH TrialValidationSummary AS (
    SELECT 
        b.trial_id,
        COUNT(b.raw_id) AS total_raw_records,
        COUNT(q.quarantine_id) AS total_quarantined_records,
        COUNT(b.raw_id) - COUNT(q.quarantine_id) AS valid_records
    FROM bronze_clinical_trials b
    LEFT JOIN quarantine_clinical_trials q ON b.raw_id = q.raw_id
    GROUP BY b.trial_id
)
SELECT 
    trial_id,
    total_raw_records,
    valid_records,
    total_quarantined_records,
    ROUND((valid_records::NUMERIC / total_raw_records::NUMERIC) * 100, 2) AS pass_rate_pct
FROM TrialValidationSummary
ORDER BY pass_rate_pct DESC;

-- 3. Chained CTEs for Patient-Level Timeline Sanity
-- Business Goal: Identify patients enrolled in multiple trials across dates
WITH CleanDates AS (
    SELECT 
        patient_id,
        trial_id,
        CAST(start_date AS DATE) AS start_dt,
        CAST(end_date AS DATE) AS end_dt
    FROM bronze_clinical_trials
    WHERE start_date ~ '^\d{4}-\d{2}-\d{2}$'
      AND end_date ~ '^\d{4}-\d{2}-\d{2}$'
),
TrialDurations AS (
    SELECT 
        patient_id,
        trial_id,
        start_dt,
        end_dt,
        (end_dt - start_dt) AS duration_days
    FROM CleanDates
)
SELECT 
    patient_id,
    trial_id,
    duration_days
FROM TrialDurations
WHERE duration_days > 0
ORDER BY duration_days DESC
LIMIT 10;

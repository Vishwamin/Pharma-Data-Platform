-- ============================================================================
-- SQL MODULE 2: Aggregations & Grouping (GROUP BY, HAVING, Aggregates)
-- Database: pharma_clinical_db
-- ============================================================================

-- 1. Counting records and calculating metrics grouped by Trial ID
-- Business Goal: Summarize patient counts and outcome counts per clinical trial
SELECT 
    trial_id,
    COUNT(*) AS total_enrolled_patients,
    COUNT(outcome) AS completed_outcome_records,
    COUNT(*) - COUNT(outcome) AS missing_outcome_count
FROM bronze_clinical_trials
GROUP BY trial_id
ORDER BY total_enrolled_patients DESC;

-- 2. Grouping by treatment arm with HAVING clause filter
-- Business Goal: Find treatment arms with more than 100 enrolled records
SELECT 
    treatment,
    COUNT(patient_id) AS total_patients,
    COUNT(DISTINCT patient_id) AS unique_patients
FROM bronze_clinical_trials
WHERE treatment IS NOT NULL AND treatment != 'N/A'
GROUP BY treatment
HAVING COUNT(patient_id) > 100
ORDER BY total_patients DESC;

-- 3. Min, Max, and Average Dosage across treatments (handling raw text numbers)
-- Business Goal: Calculate dosage statistics per treatment arm
SELECT 
    treatment,
    COUNT(*) AS record_count,
    ROUND(AVG(CAST(dosage AS NUMERIC)), 2) AS avg_dosage_mg,
    MIN(CAST(dosage AS NUMERIC)) AS min_dosage_mg,
    MAX(CAST(dosage AS NUMERIC)) AS max_dosage_mg
FROM bronze_clinical_trials
WHERE dosage ~ '^[0-9]+(\.[0-9]+)?$'  -- Regex check to exclude non-numeric corrupted strings
GROUP BY treatment
ORDER BY avg_dosage_mg DESC;

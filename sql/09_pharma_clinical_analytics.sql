-- ============================================================================
-- SQL MODULE 9: Real-World Clinical Trial Analytics Queries
-- Database: pharma_clinical_db
-- ============================================================================

-- 1. Efficacy Rate per Treatment Arm
-- Business Goal: Calculate percentage of completed/effective outcomes per drug treatment
SELECT 
    treatment,
    COUNT(*) AS total_patients_treated,
    COUNT(*) FILTER (WHERE outcome IN ('Completed', 'Effective')) AS successful_outcomes,
    COUNT(*) FILTER (WHERE outcome = 'Adverse Event') AS adverse_event_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE outcome IN ('Completed', 'Effective')) / COUNT(*), 2) AS efficacy_rate_pct,
    ROUND(100.0 * COUNT(*) FILTER (WHERE outcome = 'Adverse Event') / COUNT(*), 2) AS adverse_event_rate_pct
FROM bronze_clinical_trials
WHERE treatment IS NOT NULL AND treatment != 'N/A'
GROUP BY treatment
ORDER BY efficacy_rate_pct DESC;

-- 2. Country-wise Clinical Trial Participation Matrix
-- Business Goal: Cross-tabulate patient count and adverse events across geographic regions
SELECT 
    country,
    COUNT(DISTINCT trial_id) AS active_trials,
    COUNT(DISTINCT patient_id) AS total_patients,
    COUNT(*) FILTER (WHERE outcome = 'Adverse Event') AS total_adverse_events
FROM bronze_clinical_trials
WHERE country IS NOT NULL
GROUP BY country
ORDER BY total_patients DESC;

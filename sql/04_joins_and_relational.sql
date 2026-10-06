-- ============================================================================
-- SQL MODULE 4: JOINs & Relational Auditing (INNER JOIN, LEFT JOIN)
-- Database: pharma_clinical_db
-- ============================================================================

-- 1. LEFT JOIN between Bronze landing records and Quarantine table
-- Business Goal: Reconcile all Bronze raw records with their Quarantine status
SELECT 
    b.raw_id,
    b.patient_id,
    b.trial_id,
    b.treatment,
    b.dosage,
    CASE 
        WHEN q.quarantine_id IS NOT NULL THEN 'QUARANTINED'
        ELSE 'VALID / APPROVED'
    END AS quality_status,
    q.violation_reasons
FROM bronze_clinical_trials b
LEFT JOIN quarantine_clinical_trials q 
       ON b.raw_id = q.raw_id
ORDER BY b.raw_id
LIMIT 15;

-- 2. INNER JOIN to analyze ONLY quarantined records alongside raw values
-- Business Goal: Inspect exact raw corrupted payloads that failed data quality validation
SELECT 
    b.raw_id,
    b.patient_id,
    b.age AS raw_age_value,
    b.dosage AS raw_dosage_value,
    q.violation_reasons,
    q.quarantined_at
FROM bronze_clinical_trials b
INNER JOIN quarantine_clinical_trials q 
        ON b.raw_id = q.raw_id
ORDER BY q.quarantine_id ASC
LIMIT 10;

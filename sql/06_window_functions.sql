-- ============================================================================
-- SQL MODULE 6: Window Functions (ROW_NUMBER, RANK, DENSE_RANK, LAG, LEAD, OVER)
-- Database: pharma_clinical_db
-- ============================================================================

-- 1. Deduplication using ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)
-- Business Goal: Assign a unique row rank per patient-trial pair to isolate exact duplicates
WITH RankedRecords AS (
    SELECT 
        raw_id,
        patient_id,
        trial_id,
        treatment,
        dosage,
        ingestion_timestamp,
        ROW_NUMBER() OVER (
            PARTITION BY patient_id, trial_id 
            ORDER BY raw_id ASC
        ) AS record_sequence
    FROM bronze_clinical_trials
)
SELECT 
    raw_id,
    patient_id,
    trial_id,
    treatment,
    record_sequence,
    CASE 
        WHEN record_sequence = 1 THEN 'KEEP (First Valid Record)'
        ELSE 'DISCARD (Duplicate Record)'
    END AS deduplication_action
FROM RankedRecords
WHERE patient_id IN (
    -- Filter to patients with known duplicate entries for demonstration
    SELECT patient_id 
    FROM bronze_clinical_trials 
    GROUP BY patient_id 
    HAVING COUNT(*) > 1
)
ORDER BY patient_id, record_sequence
LIMIT 15;

-- 2. Comparing RANK() vs DENSE_RANK() across Patient Ages
-- Business Goal: Rank oldest patients within each trial arm
SELECT 
    trial_id,
    patient_id,
    CAST(age AS INTEGER) AS age_num,
    RANK() OVER (PARTITION BY trial_id ORDER BY CAST(age AS INTEGER) DESC) AS rank_gap,
    DENSE_RANK() OVER (PARTITION BY trial_id ORDER BY CAST(age AS INTEGER) DESC) AS dense_rank_continuous
FROM bronze_clinical_trials
WHERE age ~ '^[0-9]+$'
ORDER BY trial_id, age_num DESC
LIMIT 15;

-- 3. Time-Series Windowing: LAG() and LEAD() for Patient Journey Tracking
-- Business Goal: Fetch previous start_date and next treatment arm for sequential patient visits
WITH CleanVisits AS (
    SELECT 
        patient_id,
        trial_id,
        treatment,
        CAST(start_date AS DATE) AS start_dt
    FROM bronze_clinical_trials
    WHERE start_date ~ '^\d{4}-\d{2}-\d{2}$'
)
SELECT 
    patient_id,
    start_dt,
    treatment,
    LAG(treatment, 1) OVER (PARTITION BY patient_id ORDER BY start_dt) AS previous_treatment,
    LEAD(start_dt, 1) OVER (PARTITION BY patient_id ORDER BY start_dt) AS next_visit_date,
    start_dt - LAG(start_dt, 1) OVER (PARTITION BY patient_id ORDER BY start_dt) AS days_since_last_visit
FROM CleanVisits
ORDER BY patient_id, start_dt
LIMIT 15;

-- 4. Cumulative Aggregations: Running SUM and AVG OVER (PARTITION BY ...)
-- Business Goal: Compute cumulative patient enrollment count per trial over time
WITH EnrollmentTimeline AS (
    SELECT 
        trial_id,
        CAST(start_date AS DATE) AS start_dt,
        COUNT(*) AS daily_enrollments
    FROM bronze_clinical_trials
    WHERE start_date ~ '^\d{4}-\d{2}-\d{2}$'
    GROUP BY trial_id, CAST(start_date AS DATE)
)
SELECT 
    trial_id,
    start_dt,
    daily_enrollments,
    SUM(daily_enrollments) OVER (
        PARTITION BY trial_id 
        ORDER BY start_dt 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_running_enrollment,
    ROUND(AVG(daily_enrollments) OVER (
        PARTITION BY trial_id 
        ORDER BY start_dt 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) AS 7_day_moving_avg_enrollment
FROM EnrollmentTimeline
ORDER BY trial_id, start_dt
LIMIT 15;

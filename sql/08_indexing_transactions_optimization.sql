-- ============================================================================
-- SQL MODULE 8: Indexing, Transactions & Query Optimization
-- Database: pharma_clinical_db
-- ============================================================================

-- 1. Analyzing Query Execution Plan before Indexing (EXPLAIN ANALYZE)
-- Business Goal: Measure execution time for filtering by trial_id and patient_id
EXPLAIN ANALYZE 
SELECT * 
FROM bronze_clinical_trials 
WHERE trial_id = 'CT-101' 
  AND patient_id = 'P1005';

-- 2. Creating B-Tree Single Column and Composite Indexes
-- Business Goal: Accelerate lookup speed on foreign keys and business search filters
CREATE INDEX IF NOT EXISTS idx_bronze_patient_trial 
ON bronze_clinical_trials (patient_id, trial_id);

CREATE INDEX IF NOT EXISTS idx_quarantine_raw_id 
ON quarantine_clinical_trials (raw_id);

-- 3. Re-evaluating Query Execution Plan after Indexing
-- Business Goal: Confirm Index Scan replaces Sequential Table Scan
EXPLAIN ANALYZE 
SELECT * 
FROM bronze_clinical_trials 
WHERE trial_id = 'CT-101' 
  AND patient_id = 'P1005';

-- 4. ACID Transaction Example (BEGIN, SAVEPOINT, COMMIT, ROLLBACK)
-- Business Goal: Safely isolate dirty batch updates inside a transactional block
BEGIN;

-- Create temporary savepoint
SAVEPOINT before_batch_update;

-- Perform transactional update
UPDATE bronze_clinical_trials
SET outcome = 'Pending Review'
WHERE outcome IS NULL;

-- Audit affected count
SELECT COUNT(*) FROM bronze_clinical_trials WHERE outcome = 'Pending Review';

-- Rollback to original state (safely undo change for demo)
ROLLBACK TO SAVEPOINT before_batch_update;

-- Commit clean session state
COMMIT;

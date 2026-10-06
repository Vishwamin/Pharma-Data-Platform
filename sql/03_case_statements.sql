-- ============================================================================
-- SQL MODULE 3: CASE Statements (Conditional Logic & Categorical Cleaning)
-- Database: pharma_clinical_db
-- ============================================================================

-- 1. Categorizing patients into Demography Age Buckets
-- Business Goal: Group trial participants into standard pharma age demographics
SELECT 
    patient_id,
    age,
    CASE 
        WHEN age ~ '^-?[0-9]+$' AND CAST(age AS INTEGER) < 18 THEN 'Pediatric (<18)'
        WHEN age ~ '^-?[0-9]+$' AND CAST(age AS INTEGER) BETWEEN 18 AND 39 THEN 'Young Adult (18-39)'
        WHEN age ~ '^-?[0-9]+$' AND CAST(age AS INTEGER) BETWEEN 40 AND 64 THEN 'Middle Adult (40-64)'
        WHEN age ~ '^-?[0-9]+$' AND CAST(age AS INTEGER) >= 65 AND CAST(age AS INTEGER) <= 100 THEN 'Senior (65+)'
        ELSE 'Invalid / Corrupted Age'
    END AS age_demographic_group
FROM bronze_clinical_trials
LIMIT 15;

-- 2. Standardizing messy raw country names using CASE
-- Business Goal: Normalize raw variations ('US', 'UNITED STATES') into 'USA'
SELECT 
    country AS raw_country_value,
    CASE 
        WHEN UPPER(TRIM(country)) IN ('US', 'UNITED STATES', 'USA') THEN 'USA'
        WHEN UPPER(TRIM(country)) IN ('GERMANY', 'DE') THEN 'Germany'
        WHEN UPPER(TRIM(country)) IN ('JAPAN', 'JP') THEN 'Japan'
        WHEN UPPER(TRIM(country)) IN ('UK', 'UNITED KINGDOM') THEN 'UK'
        ELSE COALESCE(country, 'Unknown')
    END AS standardized_country,
    COUNT(*) AS record_count
FROM bronze_clinical_trials
GROUP BY 1, 2
ORDER BY record_count DESC;

-- 3. Flagging Efficacy vs Safety outcomes
-- Business Goal: Classify trial outcomes into Clinical Efficacy vs Safety Events
SELECT 
    outcome,
    CASE 
        WHEN outcome IN ('Completed', 'Effective') THEN 'Positive Response'
        WHEN outcome = 'Adverse Event' THEN 'Safety Violation Flag'
        WHEN outcome = 'Withdrawn' THEN 'Patient Withdrawal'
        ELSE 'Unresolved / Missing'
    END AS clinical_response_category,
    COUNT(*) AS total_patients
FROM bronze_clinical_trials
GROUP BY outcome, 2
ORDER BY total_patients DESC;

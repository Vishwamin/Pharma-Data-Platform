-- =============================================================================
-- Phase 9: PostgreSQL Database Initialization Script
-- =============================================================================
-- Executed automatically on container initialization by postgres:15-alpine
-- via /docker-entrypoint-initdb.d/
-- =============================================================================

-- Ensure target database exists
SELECT 'CREATE DATABASE pharma_clinical_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'pharma_clinical_db')\gexec

-- Grant full privileges to application user
GRANT ALL PRIVILEGES ON DATABASE pharma_clinical_db TO pharma_admin;

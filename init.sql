-- Initialize Stanford Research Opportunities Database
-- This file runs when the PostgreSQL container starts for the first time

-- Create pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Create user if it doesn't exist (for Railway compatibility)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'postgres') THEN
        CREATE USER postgres WITH SUPERUSER CREATEDB CREATEROLE LOGIN;
    END IF;
END
$$;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE stanford_opportunities TO postgres;

-- Create schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS public;

-- Set default permissions
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO postgres;

-- Log initialization
INSERT INTO pg_stat_statements_reset() VALUES (DEFAULT) ON CONFLICT DO NOTHING; 
-- =============================================================================
-- Pilot Space PostgreSQL Extensions Initialization
-- =============================================================================
-- This script runs automatically when the postgres container is first created.
-- It enables required extensions for the Pilot Space application.
-- =============================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector for AI embeddings and vector similarity search
CREATE EXTENSION IF NOT EXISTS "vector";

-- Enable pg_trgm for fuzzy text search
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Enable btree_gist for exclusion constraints (useful for scheduling)
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- Enable pgcrypto for cryptographic functions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enable pg_stat_statements for query performance monitoring (optional but recommended)
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Pilot Space PostgreSQL extensions initialized successfully';
END $$;

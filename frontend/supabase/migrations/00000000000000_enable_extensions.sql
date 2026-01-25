-- ============================================
-- Pilot Space - Enable Required Extensions
-- ============================================
-- This migration enables all PostgreSQL extensions required by Pilot Space.
-- Extensions are installed in the 'extensions' schema by convention.
--
-- Required for:
-- - pgvector: RAG/semantic search (3072 dimensions for text-embedding-3-large)
-- - pg_net: HTTP requests from database (for Edge Function calls)
-- - pg_cron: Scheduled tasks (embedding jobs, cleanup)
-- - pgmq: Message queues (background job processing)
-- - hstore: Key-value operations (utility functions)
-- ============================================

-- Create extensions schema if not exists
CREATE SCHEMA IF NOT EXISTS extensions;

-- ============================================
-- VECTOR DATABASE (pgvector)
-- For semantic search and RAG retrieval
-- ============================================
CREATE EXTENSION IF NOT EXISTS vector
  WITH SCHEMA extensions;

-- ============================================
-- HTTP REQUESTS (pg_net)
-- For calling Edge Functions from database triggers
-- ============================================
CREATE EXTENSION IF NOT EXISTS pg_net
  WITH SCHEMA extensions;

-- ============================================
-- SCHEDULED TASKS (pg_cron)
-- For recurring background jobs
-- ============================================
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Grant usage to postgres role
GRANT USAGE ON SCHEMA cron TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA cron TO postgres;

-- ============================================
-- MESSAGE QUEUES (pgmq)
-- For background job processing
-- ============================================
CREATE EXTENSION IF NOT EXISTS pgmq;

-- ============================================
-- KEY-VALUE OPERATIONS (hstore)
-- For utility functions
-- ============================================
CREATE EXTENSION IF NOT EXISTS hstore
  WITH SCHEMA extensions;

-- ============================================
-- UUID GENERATION (pgcrypto)
-- For secure UUID and password generation
-- ============================================
CREATE EXTENSION IF NOT EXISTS pgcrypto
  WITH SCHEMA extensions;

-- ============================================
-- FULL TEXT SEARCH (pg_trgm)
-- For typo-tolerant text search
-- ============================================
CREATE EXTENSION IF NOT EXISTS pg_trgm
  WITH SCHEMA extensions;

-- ============================================
-- UTILITY SCHEMA
-- For custom utility functions
-- ============================================
CREATE SCHEMA IF NOT EXISTS util;

-- Grant usage to authenticated users
GRANT USAGE ON SCHEMA util TO authenticated;
GRANT USAGE ON SCHEMA extensions TO authenticated;

-- ============================================
-- VERIFY EXTENSIONS
-- ============================================
DO $$
DECLARE
  ext_name text;
  required_extensions text[] := ARRAY[
    'vector',
    'pg_net',
    'pg_cron',
    'pgmq',
    'hstore',
    'pgcrypto',
    'pg_trgm'
  ];
BEGIN
  FOREACH ext_name IN ARRAY required_extensions LOOP
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = ext_name) THEN
      RAISE WARNING 'Extension % is not installed', ext_name;
    ELSE
      RAISE NOTICE 'Extension % is installed', ext_name;
    END IF;
  END LOOP;
END $$;

-- =============================================================================
-- Pilot Space - PostgreSQL Extensions Initialization
-- =============================================================================
-- This script runs automatically when the database is first created.
-- It enables all required extensions for Supabase and Pilot Space.
--
-- Extensions enabled:
--   Core Supabase: uuid-ossp, pgcrypto, pgjwt
--   AI/Vector:     vector (pgvector with HNSW)
--   Queues:        pgmq, pg_cron, pg_net
--   Search:        pg_trgm, unaccent
--   Performance:   pg_stat_statements
-- =============================================================================

-- =============================================================================
-- CREATE SCHEMAS (required before extensions and roles)
-- =============================================================================

-- Create core schemas
CREATE SCHEMA IF NOT EXISTS extensions;
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS storage;
CREATE SCHEMA IF NOT EXISTS _realtime;
CREATE SCHEMA IF NOT EXISTS realtime;

-- =============================================================================
-- CREATE ROLES (required before extensions that reference them)
-- =============================================================================

-- Anonymous role (for unauthenticated requests)
DO $$ BEGIN
  CREATE ROLE anon NOLOGIN NOINHERIT;
EXCEPTION WHEN duplicate_object THEN
  RAISE NOTICE 'Role "anon" already exists, skipping.';
END $$;

-- Authenticated role (for authenticated users)
DO $$ BEGIN
  CREATE ROLE authenticated NOLOGIN NOINHERIT;
EXCEPTION WHEN duplicate_object THEN
  RAISE NOTICE 'Role "authenticated" already exists, skipping.';
END $$;

-- Service role (for backend services with elevated privileges)
DO $$ BEGIN
  CREATE ROLE service_role NOLOGIN NOINHERIT BYPASSRLS;
EXCEPTION WHEN duplicate_object THEN
  RAISE NOTICE 'Role "service_role" already exists, skipping.';
END $$;

-- Supabase Auth admin role
DO $$ BEGIN
  CREATE ROLE supabase_auth_admin NOLOGIN NOINHERIT CREATEROLE;
EXCEPTION WHEN duplicate_object THEN
  RAISE NOTICE 'Role "supabase_auth_admin" already exists, skipping.';
END $$;

-- Supabase Storage admin role
DO $$ BEGIN
  CREATE ROLE supabase_storage_admin NOLOGIN NOINHERIT CREATEROLE;
EXCEPTION WHEN duplicate_object THEN
  RAISE NOTICE 'Role "supabase_storage_admin" already exists, skipping.';
END $$;

-- Authenticator role (for PostgREST)
DO $$ BEGIN
  CREATE ROLE authenticator NOINHERIT LOGIN PASSWORD NULL;
EXCEPTION WHEN duplicate_object THEN
  RAISE NOTICE 'Role "authenticator" already exists, skipping.';
END $$;

-- Postgres role (if not exists)
DO $$ BEGIN
  CREATE ROLE postgres SUPERUSER;
EXCEPTION WHEN duplicate_object THEN
  RAISE NOTICE 'Role "postgres" already exists, skipping.';
END $$;

-- Grant role memberships for authenticator
GRANT anon TO authenticator;
GRANT authenticated TO authenticator;
GRANT service_role TO authenticator;

-- Grant schema ownership
GRANT ALL ON SCHEMA auth TO supabase_auth_admin;
GRANT ALL ON SCHEMA storage TO supabase_storage_admin;
GRANT supabase_auth_admin TO supabase_admin;
GRANT supabase_storage_admin TO supabase_admin;

-- Grant basic schema usage
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;

-- =============================================================================
-- SUPABASE REQUIRED EXTENSIONS
-- =============================================================================

-- UUID generation (required by Supabase)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA extensions;

-- Cryptographic functions (required by Supabase)
CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA extensions;

-- JWT generation/validation (required by Supabase)
CREATE EXTENSION IF NOT EXISTS "pgjwt" WITH SCHEMA extensions;

-- HTTP client for pg_net (required for webhooks, Edge Functions)
CREATE EXTENSION IF NOT EXISTS "pg_net" WITH SCHEMA extensions;

-- =============================================================================
-- AI/VECTOR EXTENSIONS
-- =============================================================================

-- pgvector for AI embeddings and vector similarity search
-- Supports HNSW and IVFFlat indexes
CREATE EXTENSION IF NOT EXISTS "vector";

-- =============================================================================
-- QUEUE/SCHEDULING EXTENSIONS
-- =============================================================================

-- pgmq for Postgres-native message queues (Supabase Queues)
CREATE EXTENSION IF NOT EXISTS "pgmq";

-- pg_cron for scheduled jobs (background tasks, cleanup, etc.)
CREATE EXTENSION IF NOT EXISTS "pg_cron";

-- =============================================================================
-- SEARCH/TEXT EXTENSIONS
-- =============================================================================

-- Trigram similarity for fuzzy text search
CREATE EXTENSION IF NOT EXISTS "pg_trgm" WITH SCHEMA extensions;

-- Unaccent for accent-insensitive search
CREATE EXTENSION IF NOT EXISTS "unaccent" WITH SCHEMA extensions;

-- =============================================================================
-- PERFORMANCE/MONITORING EXTENSIONS
-- =============================================================================

-- Query performance monitoring
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- B-tree GiST for exclusion constraints (scheduling, ranges)
CREATE EXTENSION IF NOT EXISTS "btree_gist" WITH SCHEMA extensions;

-- hstore for key-value storage (used by utility functions)
CREATE EXTENSION IF NOT EXISTS "hstore" WITH SCHEMA extensions;

-- =============================================================================
-- GRANT PERMISSIONS
-- =============================================================================

-- Grant usage on extensions schema to all roles
GRANT USAGE ON SCHEMA extensions TO postgres, anon, authenticated, service_role;

-- Grant execute on all functions in extensions schema
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA extensions TO postgres, anon, authenticated, service_role;

-- Allow cron jobs to be scheduled by authenticated users
GRANT USAGE ON SCHEMA cron TO postgres, service_role;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA cron TO postgres, service_role;

-- =============================================================================
-- VERIFICATION
-- =============================================================================

DO $$
DECLARE
    ext_record RECORD;
    schema_count INTEGER;
    role_count INTEGER;
BEGIN
    RAISE NOTICE '=== Pilot Space Initialization Verification ===';

    -- Count schemas
    SELECT COUNT(*) INTO schema_count
    FROM pg_namespace
    WHERE nspname IN ('extensions', 'auth', 'storage', '_realtime', 'realtime');
    RAISE NOTICE 'Schemas created: % (extensions, auth, storage, _realtime, realtime)', schema_count;

    -- Count roles
    SELECT COUNT(*) INTO role_count
    FROM pg_roles
    WHERE rolname IN ('anon', 'authenticated', 'service_role', 'supabase_auth_admin', 'supabase_storage_admin', 'authenticator');
    RAISE NOTICE 'Roles created: % (anon, authenticated, service_role, supabase_auth_admin, supabase_storage_admin, authenticator)', role_count;

    -- List extensions
    RAISE NOTICE 'Extensions installed:';
    FOR ext_record IN
        SELECT extname, extversion
        FROM pg_extension
        WHERE extname IN (
            'uuid-ossp', 'pgcrypto', 'pgjwt', 'pg_net',
            'vector', 'pgmq', 'pg_cron',
            'pg_trgm', 'unaccent',
            'pg_stat_statements', 'btree_gist', 'hstore'
        )
        ORDER BY extname
    LOOP
        RAISE NOTICE '  - % (v%)', ext_record.extname, ext_record.extversion;
    END LOOP;

    RAISE NOTICE '=== Initialization completed successfully ===';
END $$;

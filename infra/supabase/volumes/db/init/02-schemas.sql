-- =============================================================================
-- Pilot Space - Database Schemas Initialization
-- =============================================================================
-- Creates required schemas and utility functions for Pilot Space.
--
-- Schemas:
--   public:        Main application data (issues, notes, projects, etc.)
--   auth:          Supabase Auth (managed by GoTrue)
--   storage:       Supabase Storage (managed by Storage API)
--   realtime:      Supabase Realtime (managed by Realtime service)
--   _realtime:     Realtime internal schema
--   _analytics:    Logflare analytics schema
--   util:          Utility functions for embeddings, queues, etc.
--   graphql_public: GraphQL public schema
-- =============================================================================

-- =============================================================================
-- CREATE SCHEMAS
-- =============================================================================

-- Utility schema for helper functions
CREATE SCHEMA IF NOT EXISTS util;

-- GraphQL public schema for pg_graphql
CREATE SCHEMA IF NOT EXISTS graphql_public;

-- Analytics schema for Logflare
CREATE SCHEMA IF NOT EXISTS _analytics;

-- =============================================================================
-- SCHEMA PERMISSIONS
-- =============================================================================

-- Grant usage on all schemas to appropriate roles
GRANT USAGE ON SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT USAGE ON SCHEMA util TO postgres, anon, authenticated, service_role;
GRANT USAGE ON SCHEMA graphql_public TO postgres, anon, authenticated, service_role;

-- Service role gets full access to all schemas
GRANT ALL PRIVILEGES ON SCHEMA public TO service_role;
GRANT ALL PRIVILEGES ON SCHEMA util TO service_role;

-- =============================================================================
-- UTILITY FUNCTIONS - Project URL (for Edge Functions)
-- =============================================================================

-- Get Supabase project URL from Vault (for Edge Function invocation)
CREATE OR REPLACE FUNCTION util.project_url()
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  secret_value text;
BEGIN
  -- Try to get from Vault first
  BEGIN
    SELECT decrypted_secret INTO secret_value
    FROM vault.decrypted_secrets
    WHERE name = 'project_url';
  EXCEPTION WHEN OTHERS THEN
    -- Fallback to environment variable or default
    secret_value := current_setting('app.settings.project_url', true);
  END;

  -- Return default if not found
  RETURN COALESCE(secret_value, 'http://kong:8000');
END;
$$;

-- =============================================================================
-- UTILITY FUNCTIONS - Edge Function Invocation
-- =============================================================================

-- Invoke any Edge Function via HTTP
CREATE OR REPLACE FUNCTION util.invoke_edge_function(
  name text,
  body jsonb,
  timeout_milliseconds int DEFAULT 300000  -- 5 minute default
)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  headers_raw text;
  auth_header text;
  project_url text;
BEGIN
  -- Get project URL
  project_url := util.project_url();

  -- Try to reuse request headers for authorization (if in PostgREST context)
  headers_raw := current_setting('request.headers', true);

  auth_header := CASE
    WHEN headers_raw IS NOT NULL THEN
      (headers_raw::json->>'authorization')
    ELSE
      NULL
  END;

  -- Make async HTTP request to the edge function
  PERFORM net.http_post(
    url => project_url || '/functions/v1/' || name,
    headers => jsonb_build_object(
      'Content-Type', 'application/json',
      'Authorization', auth_header
    ),
    body => body,
    timeout_milliseconds => timeout_milliseconds
  );
END;
$$;

-- =============================================================================
-- UTILITY FUNCTIONS - Column Clearing (for embeddings)
-- =============================================================================

-- Generic trigger function to clear a column on update
CREATE OR REPLACE FUNCTION util.clear_column()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    clear_column text := TG_ARGV[0];
BEGIN
    NEW := NEW #= hstore(clear_column, NULL);
    RETURN NEW;
END;
$$;

-- =============================================================================
-- UTILITY FUNCTIONS - Timestamp Management
-- =============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION util.update_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

-- =============================================================================
-- EMBEDDING QUEUE SETUP
-- =============================================================================

-- Create embedding jobs queue using pgmq
SELECT pgmq.create('embedding_jobs');

-- Generic trigger function to queue embedding jobs
CREATE OR REPLACE FUNCTION util.queue_embeddings()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  content_function text = TG_ARGV[0];
  embedding_column text = TG_ARGV[1];
BEGIN
  PERFORM pgmq.send(
    queue_name => 'embedding_jobs',
    msg => jsonb_build_object(
      'id', NEW.id,
      'schema', TG_TABLE_SCHEMA,
      'table', TG_TABLE_NAME,
      'contentFunction', content_function,
      'embeddingColumn', embedding_column
    )
  );
  RETURN NEW;
END;
$$;

-- Function to process embedding jobs from the queue
CREATE OR REPLACE FUNCTION util.process_embeddings(
  batch_size int DEFAULT 10,
  max_requests int DEFAULT 10,
  timeout_milliseconds int DEFAULT 300000  -- 5 minute default
)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  job_batches jsonb[];
  batch jsonb;
BEGIN
  WITH
    -- Get jobs and assign batch numbers
    numbered_jobs AS (
      SELECT
        message || jsonb_build_object('jobId', msg_id) AS job_info,
        (row_number() OVER (ORDER BY 1) - 1) / batch_size AS batch_num
      FROM pgmq.read(
        queue_name => 'embedding_jobs',
        vt => timeout_milliseconds / 1000,
        qty => max_requests * batch_size
      )
    ),
    -- Group jobs into batches
    batched_jobs AS (
      SELECT
        jsonb_agg(job_info) AS batch_array,
        batch_num
      FROM numbered_jobs
      GROUP BY batch_num
    )
  -- Aggregate all batches into array
  SELECT array_agg(batch_array)
  FROM batched_jobs
  INTO job_batches;

  -- Skip if no jobs
  IF job_batches IS NULL THEN
    RETURN;
  END IF;

  -- Invoke the embed edge function for each batch
  FOREACH batch IN ARRAY job_batches LOOP
    PERFORM util.invoke_edge_function(
      name => 'embed',
      body => batch,
      timeout_milliseconds => timeout_milliseconds
    );
  END LOOP;
END;
$$;

-- =============================================================================
-- SCHEDULED JOBS (pg_cron)
-- =============================================================================

-- Schedule embedding processing every 10 seconds
SELECT cron.schedule(
  'process-embeddings',
  '10 seconds',
  $$SELECT util.process_embeddings();$$
);

-- Schedule cleanup of old completed queue messages (weekly)
SELECT cron.schedule(
  'cleanup-old-queue-messages',
  '0 3 * * 0',  -- Sunday 3 AM
  $$
    -- Clean up pgmq archive tables older than 7 days
    DELETE FROM pgmq.embedding_jobs_archive
    WHERE archived_at < NOW() - INTERVAL '7 days';
  $$
);

-- =============================================================================
-- DEFAULT TABLE SETTINGS
-- =============================================================================

-- Set default privileges for authenticated users
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO authenticated;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT EXECUTE ON FUNCTIONS TO authenticated;

-- Set default privileges for service role (full access)
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT ALL PRIVILEGES ON TABLES TO service_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT ALL PRIVILEGES ON SEQUENCES TO service_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT ALL PRIVILEGES ON FUNCTIONS TO service_role;

-- =============================================================================
-- VERIFICATION
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '=== Pilot Space Schemas Initialization Complete ===';
    RAISE NOTICE 'Schemas created: util, graphql_public, _analytics';
    RAISE NOTICE 'Utility functions installed in util schema';
    RAISE NOTICE 'Embedding queue created: embedding_jobs';
    RAISE NOTICE 'Cron jobs scheduled: process-embeddings, cleanup-old-queue-messages';
END $$;

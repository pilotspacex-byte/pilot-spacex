-- =============================================================================
-- Pilot Space - Row-Level Security (RLS) Base Policies
-- =============================================================================
-- This script sets up the foundation for RLS in Pilot Space.
-- Application-specific tables should define their own policies.
--
-- RLS Strategy:
--   - All tables MUST have RLS enabled
--   - Use helper functions for common checks (workspace membership)
--   - Service role bypasses RLS for admin operations
--   - Anon role has no access to application data by default
--
-- Multi-tenancy:
--   - Users belong to workspaces
--   - Data is isolated by workspace_id
--   - Users can only access data in workspaces they belong to
-- =============================================================================

-- =============================================================================
-- AUTH HELPER FUNCTIONS
-- =============================================================================

-- Get the current authenticated user's ID
CREATE OR REPLACE FUNCTION auth.uid()
RETURNS uuid
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT NULLIF(
    current_setting('request.jwt.claims', true)::json->>'sub',
    ''
  )::uuid;
$$;

-- Get the current role (anon, authenticated, service_role)
CREATE OR REPLACE FUNCTION auth.role()
RETURNS text
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT COALESCE(
    current_setting('request.jwt.claims', true)::json->>'role',
    'anon'
  );
$$;

-- Get the current user's email
CREATE OR REPLACE FUNCTION auth.email()
RETURNS text
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT current_setting('request.jwt.claims', true)::json->>'email';
$$;

-- Get the JWT expiration timestamp
CREATE OR REPLACE FUNCTION auth.jwt_exp()
RETURNS integer
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT (current_setting('request.jwt.claims', true)::json->>'exp')::integer;
$$;

-- =============================================================================
-- WORKSPACE MEMBERSHIP HELPERS
-- =============================================================================

-- Check if current user is a member of a workspace
-- This function is used in RLS policies
CREATE OR REPLACE FUNCTION auth.is_workspace_member(workspace_id uuid)
RETURNS boolean
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  -- Service role always has access
  IF auth.role() = 'service_role' THEN
    RETURN TRUE;
  END IF;

  -- Check workspace_members table
  RETURN EXISTS (
    SELECT 1 FROM workspace_members wm
    WHERE wm.workspace_id = is_workspace_member.workspace_id
    AND wm.user_id = auth.uid()
    AND wm.deleted_at IS NULL
  );
END;
$$;

-- Check if current user is an admin of a workspace
CREATE OR REPLACE FUNCTION auth.is_workspace_admin(workspace_id uuid)
RETURNS boolean
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  -- Service role always has access
  IF auth.role() = 'service_role' THEN
    RETURN TRUE;
  END IF;

  -- Check workspace_members table for admin/owner role
  RETURN EXISTS (
    SELECT 1 FROM workspace_members wm
    WHERE wm.workspace_id = is_workspace_admin.workspace_id
    AND wm.user_id = auth.uid()
    AND wm.role IN ('owner', 'admin')
    AND wm.deleted_at IS NULL
  );
END;
$$;

-- Check if current user is the owner of a workspace
CREATE OR REPLACE FUNCTION auth.is_workspace_owner(workspace_id uuid)
RETURNS boolean
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  -- Service role always has access
  IF auth.role() = 'service_role' THEN
    RETURN TRUE;
  END IF;

  RETURN EXISTS (
    SELECT 1 FROM workspace_members wm
    WHERE wm.workspace_id = is_workspace_owner.workspace_id
    AND wm.user_id = auth.uid()
    AND wm.role = 'owner'
    AND wm.deleted_at IS NULL
  );
END;
$$;

-- Get all workspace IDs the current user is a member of
CREATE OR REPLACE FUNCTION auth.user_workspaces()
RETURNS SETOF uuid
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT workspace_id
  FROM workspace_members
  WHERE user_id = auth.uid()
  AND deleted_at IS NULL;
$$;

-- =============================================================================
-- PROJECT ACCESS HELPERS
-- =============================================================================

-- Check if current user can access a project
CREATE OR REPLACE FUNCTION auth.can_access_project(project_id uuid)
RETURNS boolean
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  project_workspace_id uuid;
BEGIN
  -- Service role always has access
  IF auth.role() = 'service_role' THEN
    RETURN TRUE;
  END IF;

  -- Get the workspace_id for this project
  SELECT workspace_id INTO project_workspace_id
  FROM projects
  WHERE id = can_access_project.project_id
  AND deleted_at IS NULL;

  IF project_workspace_id IS NULL THEN
    RETURN FALSE;
  END IF;

  -- Check if user is member of the project's workspace
  RETURN auth.is_workspace_member(project_workspace_id);
END;
$$;

-- =============================================================================
-- RLS POLICY TEMPLATES
-- =============================================================================

-- Template: Enable RLS on a table with workspace isolation
-- Usage: SELECT util.enable_workspace_rls('issues', 'workspace_id');
CREATE OR REPLACE FUNCTION util.enable_workspace_rls(
  table_name text,
  workspace_column text DEFAULT 'workspace_id'
)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  -- Enable RLS
  EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);

  -- Select policy: Users can see rows in their workspaces
  EXECUTE format(
    'CREATE POLICY "Users can view %I in their workspaces" ON %I
     FOR SELECT USING (auth.is_workspace_member(%I))',
    table_name, table_name, workspace_column
  );

  -- Insert policy: Users can insert in their workspaces
  EXECUTE format(
    'CREATE POLICY "Users can insert %I in their workspaces" ON %I
     FOR INSERT WITH CHECK (auth.is_workspace_member(%I))',
    table_name, table_name, workspace_column
  );

  -- Update policy: Users can update in their workspaces
  EXECUTE format(
    'CREATE POLICY "Users can update %I in their workspaces" ON %I
     FOR UPDATE USING (auth.is_workspace_member(%I))',
    table_name, table_name, workspace_column
  );

  -- Delete policy: Only admins can delete
  EXECUTE format(
    'CREATE POLICY "Admins can delete %I" ON %I
     FOR DELETE USING (auth.is_workspace_admin(%I))',
    table_name, table_name, workspace_column
  );

  RAISE NOTICE 'RLS enabled for table % with workspace column %', table_name, workspace_column;
END;
$$;

-- Template: Enable RLS on a table with project isolation
CREATE OR REPLACE FUNCTION util.enable_project_rls(
  table_name text,
  project_column text DEFAULT 'project_id'
)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  -- Enable RLS
  EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);

  -- Select policy: Users can see rows in projects they can access
  EXECUTE format(
    'CREATE POLICY "Users can view %I in their projects" ON %I
     FOR SELECT USING (auth.can_access_project(%I))',
    table_name, table_name, project_column
  );

  -- Insert policy: Users can insert in projects they can access
  EXECUTE format(
    'CREATE POLICY "Users can insert %I in their projects" ON %I
     FOR INSERT WITH CHECK (auth.can_access_project(%I))',
    table_name, table_name, project_column
  );

  -- Update policy: Users can update in projects they can access
  EXECUTE format(
    'CREATE POLICY "Users can update %I in their projects" ON %I
     FOR UPDATE USING (auth.can_access_project(%I))',
    table_name, table_name, project_column
  );

  -- Delete policy: Only project admins can delete
  EXECUTE format(
    'CREATE POLICY "Admins can delete %I" ON %I
     FOR DELETE USING (
       EXISTS (
         SELECT 1 FROM projects p
         WHERE p.id = %I
         AND auth.is_workspace_admin(p.workspace_id)
       )
     )',
    table_name, table_name, project_column
  );

  RAISE NOTICE 'RLS enabled for table % with project column %', table_name, project_column;
END;
$$;

-- =============================================================================
-- STORAGE RLS POLICIES
-- =============================================================================

-- Storage objects - users can upload to their workspace folders
-- Note: storage.objects table is managed by Supabase Storage

-- Policy: Users can upload to their workspace folders
-- Bucket structure: /{workspace_id}/{user_id}/...
DO $$
BEGIN
  -- Check if storage.objects exists (it should after Storage API initializes)
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'storage' AND table_name = 'objects'
  ) THEN
    -- Enable RLS
    ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

    -- Users can view files in their workspaces
    CREATE POLICY IF NOT EXISTS "Users can view workspace files"
    ON storage.objects FOR SELECT
    USING (
      bucket_id = 'pilot-space-uploads'
      AND auth.is_workspace_member((storage.foldername(name))[1]::uuid)
    );

    -- Users can upload to their folder within workspace
    CREATE POLICY IF NOT EXISTS "Users can upload to workspace"
    ON storage.objects FOR INSERT
    WITH CHECK (
      bucket_id = 'pilot-space-uploads'
      AND (storage.foldername(name))[1]::uuid IN (SELECT auth.user_workspaces())
    );

    -- Users can update their own files
    CREATE POLICY IF NOT EXISTS "Users can update own files"
    ON storage.objects FOR UPDATE
    USING (
      bucket_id = 'pilot-space-uploads'
      AND owner = auth.uid()
    );

    -- Users can delete their own files
    CREATE POLICY IF NOT EXISTS "Users can delete own files"
    ON storage.objects FOR DELETE
    USING (
      bucket_id = 'pilot-space-uploads'
      AND owner = auth.uid()
    );

    RAISE NOTICE 'Storage RLS policies created';
  ELSE
    RAISE NOTICE 'storage.objects table not found - will be created by Storage API';
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'Storage RLS setup skipped: %', SQLERRM;
END $$;

-- =============================================================================
-- VERIFICATION
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '=== Pilot Space RLS Initialization Complete ===';
    RAISE NOTICE 'Auth helper functions: auth.uid(), auth.role(), auth.email()';
    RAISE NOTICE 'Workspace helpers: auth.is_workspace_member(), auth.is_workspace_admin()';
    RAISE NOTICE 'Project helpers: auth.can_access_project()';
    RAISE NOTICE 'RLS templates: util.enable_workspace_rls(), util.enable_project_rls()';
END $$;

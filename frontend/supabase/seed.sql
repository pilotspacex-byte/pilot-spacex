-- ============================================
-- Pilot Space - Seed Data
-- ============================================
-- This file contains initial seed data for local development.
-- It runs after all migrations when using `supabase db reset`.
--
-- Usage:
--   supabase db reset  (applies migrations + seed)
--   supabase db seed   (applies seed only)
--
-- Note: Do NOT add production data here. This is for development only.
-- ============================================

-- ============================================
-- DEVELOPMENT HELPERS
-- ============================================

-- Create a test user function (for development only)
-- This allows creating users without email verification
CREATE OR REPLACE FUNCTION dev_create_test_user(
  p_email text,
  p_password text,
  p_name text DEFAULT 'Test User'
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  new_user_id uuid;
BEGIN
  -- Only allow in development
  IF current_setting('app.settings.environment', true) = 'production' THEN
    RAISE EXCEPTION 'Cannot create test users in production';
  END IF;

  -- Insert into auth.users (simplified for dev)
  INSERT INTO auth.users (
    id,
    instance_id,
    aud,
    role,
    email,
    encrypted_password,
    email_confirmed_at,
    raw_app_meta_data,
    raw_user_meta_data,
    created_at,
    updated_at
  ) VALUES (
    gen_random_uuid(),
    '00000000-0000-0000-0000-000000000000',
    'authenticated',
    'authenticated',
    p_email,
    crypt(p_password, gen_salt('bf')),
    now(),
    '{"provider": "email", "providers": ["email"]}'::jsonb,
    jsonb_build_object('name', p_name),
    now(),
    now()
  )
  RETURNING id INTO new_user_id;

  RETURN new_user_id;
END;
$$;

-- ============================================
-- SAMPLE DATA TEMPLATES
-- ============================================
-- Uncomment and modify these sections as needed for development

/*
-- Sample workspace
INSERT INTO workspaces (id, name, slug, description, created_by_id)
VALUES (
  '11111111-1111-1111-1111-111111111111',
  'Pilot Space Demo',
  'pilot-space-demo',
  'Demo workspace for Pilot Space development',
  (SELECT id FROM auth.users WHERE email = 'admin@example.com' LIMIT 1)
);

-- Sample project
INSERT INTO projects (id, workspace_id, name, key, description)
VALUES (
  '22222222-2222-2222-2222-222222222222',
  '11111111-1111-1111-1111-111111111111',
  'Pilot Space MVP',
  'PILOT',
  'Main project for Pilot Space MVP development'
);

-- Sample issue states
INSERT INTO issue_states (workspace_id, name, "group", color, position, is_default) VALUES
  ('11111111-1111-1111-1111-111111111111', 'Backlog', 'backlog', '#8B8B8B', 0, true),
  ('11111111-1111-1111-1111-111111111111', 'To Do', 'unstarted', '#3F76FF', 1, false),
  ('11111111-1111-1111-1111-111111111111', 'In Progress', 'started', '#F5A623', 2, false),
  ('11111111-1111-1111-1111-111111111111', 'In Review', 'started', '#9B59B6', 3, false),
  ('11111111-1111-1111-1111-111111111111', 'Done', 'completed', '#4CAF50', 4, false),
  ('11111111-1111-1111-1111-111111111111', 'Cancelled', 'cancelled', '#E74C3C', 5, false);

-- Sample labels
INSERT INTO labels (workspace_id, name, color, description) VALUES
  ('11111111-1111-1111-1111-111111111111', 'bug', '#E74C3C', 'Something is broken'),
  ('11111111-1111-1111-1111-111111111111', 'feature', '#4CAF50', 'New functionality'),
  ('11111111-1111-1111-1111-111111111111', 'enhancement', '#3F76FF', 'Improvement to existing functionality'),
  ('11111111-1111-1111-1111-111111111111', 'documentation', '#9B59B6', 'Documentation updates'),
  ('11111111-1111-1111-1111-111111111111', 'ai-generated', '#F5A623', 'Created or enhanced by AI');
*/

-- ============================================
-- CLEANUP DEVELOPMENT FUNCTIONS
-- ============================================
-- Remove dev-only functions in production deployments
-- DROP FUNCTION IF EXISTS dev_create_test_user;

-- ============================================
-- END OF SEED DATA
-- ============================================

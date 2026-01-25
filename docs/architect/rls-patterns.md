# Row-Level Security (RLS) Patterns

**Status**: Adopted (Session 2026-01-22)
**Platform**: Supabase with PostgreSQL 16+
**Reference**: Constitution v1.1.0 - Technology Standards

---

## Overview

Pilot Space uses **Row-Level Security (RLS)** as the primary authorization mechanism, enforced at the database level. This ensures data isolation even if application-level bugs exist.

### Key Principles

| Principle | Implementation |
|-----------|----------------|
| **Defense in Depth** | RLS + Application checks, not either/or |
| **Workspace Isolation** | All tenant data scoped by `workspace_id` |
| **Role-Based Access** | Policies use `workspace_members.role` |
| **Audit Trail** | All policy evaluations logged |
| **Fail Secure** | Default deny if no policy matches |

---

## RLS Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              REQUEST FLOW                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  USER               SUPABASE AUTH           DATABASE                         │
│    │                     │                      │                            │
│    ├── JWT Token ───────>│                      │                            │
│    │                     ├── auth.uid() ───────>│                            │
│    │                     │   auth.jwt() ───────>│                            │
│    │                     │                      │                            │
│    ├── Query ────────────┼──────────────────────>│                            │
│    │                     │                      ├── Check RLS Policies        │
│    │                     │                      │   ┌────────────────────┐   │
│    │                     │                      │   │ SELECT auth.uid()  │   │
│    │                     │                      │   │ = created_by_id    │   │
│    │                     │                      │   │ OR workspace_role  │   │
│    │                     │                      │   │ IN ('admin','owner')│   │
│    │                     │                      │   └────────────────────┘   │
│    │                     │                      │                            │
│    │<─── Filtered Rows ──┼──────────────────────┤                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Policies

### 1. Workspace Isolation Policy

Every user-data table includes `workspace_id` for tenant isolation:

```sql
-- Enable RLS on all user-data tables
ALTER TABLE issues ENABLE ROW LEVEL SECURITY;
ALTER TABLE notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE cycles ENABLE ROW LEVEL SECURITY;
ALTER TABLE modules ENABLE ROW LEVEL SECURITY;

-- Helper function: Get user's workspace IDs
CREATE OR REPLACE FUNCTION auth.user_workspace_ids()
RETURNS uuid[] AS $$
  SELECT ARRAY_AGG(workspace_id)
  FROM workspace_members
  WHERE user_id = auth.uid()
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- Helper function: Get user's role in a workspace
CREATE OR REPLACE FUNCTION auth.workspace_role(ws_id uuid)
RETURNS text AS $$
  SELECT role
  FROM workspace_members
  WHERE user_id = auth.uid()
  AND workspace_id = ws_id
$$ LANGUAGE sql SECURITY DEFINER STABLE;
```

### 2. Issues Table Policies

```sql
-- SELECT: Users can view issues in their workspaces
-- Guests can only view issues assigned to them (per role hierarchy spec)
CREATE POLICY "Users can view issues in their workspaces"
  ON issues FOR SELECT
  USING (
    workspace_id = ANY(auth.user_workspace_ids())
    AND deleted_at IS NULL
    AND (
      -- Non-guests can view all workspace issues
      NOT auth.is_workspace_guest(workspace_id)
      -- Guests can only view assigned issues
      OR assignee_id = auth.uid()
    )
  );

-- INSERT: Non-guest members can create issues
-- Guests have read-only access and cannot create issues
CREATE POLICY "Members can create issues"
  ON issues FOR INSERT
  WITH CHECK (
    auth.is_content_creator(workspace_id)
    AND created_by_id = auth.uid()
  );

-- UPDATE: Creator, assignee, or admin/owner can update
CREATE POLICY "Authorized users can update issues"
  ON issues FOR UPDATE
  USING (
    workspace_id = ANY(auth.user_workspace_ids())
    AND deleted_at IS NULL
    AND (
      created_by_id = auth.uid()
      OR assignee_id = auth.uid()
      OR auth.workspace_role(workspace_id) IN ('admin', 'owner')
    )
  )
  WITH CHECK (
    workspace_id = ANY(auth.user_workspace_ids())
  );

-- DELETE (soft): Creator or admin/owner can delete
CREATE POLICY "Authorized users can soft-delete issues"
  ON issues FOR UPDATE
  USING (
    workspace_id = ANY(auth.user_workspace_ids())
    AND (
      created_by_id = auth.uid()
      OR auth.workspace_role(workspace_id) IN ('admin', 'owner')
    )
  )
  WITH CHECK (
    deleted_at IS NOT NULL  -- Only allow setting deleted_at
  );
```

### 3. Notes Table Policies

```sql
-- SELECT: Users can view notes in their workspaces
-- Guests cannot view notes (they only have access to assigned issues)
CREATE POLICY "Users can view notes in their workspaces"
  ON notes FOR SELECT
  USING (
    workspace_id = ANY(auth.user_workspace_ids())
    AND deleted_at IS NULL
    AND NOT auth.is_workspace_guest(workspace_id)
  );

-- INSERT: Non-guest members can create notes
CREATE POLICY "Members can create notes"
  ON notes FOR INSERT
  WITH CHECK (
    auth.is_content_creator(workspace_id)
    AND created_by_id = auth.uid()
  );

-- UPDATE: Creator or admin/owner can update
CREATE POLICY "Authorized users can update notes"
  ON notes FOR UPDATE
  USING (
    workspace_id = ANY(auth.user_workspace_ids())
    AND deleted_at IS NULL
    AND (
      created_by_id = auth.uid()
      OR auth.workspace_role(workspace_id) IN ('admin', 'owner')
    )
  );
```

### 4. Workspace Members Policy

```sql
-- SELECT: Users can see members of their workspaces
CREATE POLICY "Users can view workspace members"
  ON workspace_members FOR SELECT
  USING (
    workspace_id = ANY(auth.user_workspace_ids())
  );

-- INSERT: Only admin/owner can add members
CREATE POLICY "Admins can add workspace members"
  ON workspace_members FOR INSERT
  WITH CHECK (
    auth.workspace_role(workspace_id) IN ('admin', 'owner')
  );

-- UPDATE: Only owner can change roles
CREATE POLICY "Owners can modify member roles"
  ON workspace_members FOR UPDATE
  USING (
    auth.workspace_role(workspace_id) = 'owner'
  );

-- DELETE: Admin/owner can remove members (except owner removing themselves)
CREATE POLICY "Admins can remove members"
  ON workspace_members FOR DELETE
  USING (
    auth.workspace_role(workspace_id) IN ('admin', 'owner')
    AND NOT (
      user_id = auth.uid()
      AND role = 'owner'
    )
  );
```

### 5. Public Project Access

Projects can be marked as public for read-only access by anyone (authenticated or not):

```sql
-- Helper function: Check if project is public
CREATE OR REPLACE FUNCTION public.is_public_project(proj_id uuid)
RETURNS boolean AS $$
  SELECT EXISTS (
    SELECT 1 FROM projects
    WHERE id = proj_id
    AND is_public = true
  )
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- Projects: Add public read access
CREATE POLICY "Public projects are readable by anyone"
  ON projects FOR SELECT
  USING (
    is_public = true
    OR workspace_id = ANY(auth.user_workspace_ids())
  );

-- Issues in public projects: Read-only access for anyone
CREATE POLICY "Issues in public projects are readable"
  ON issues FOR SELECT
  USING (
    (
      -- Member access
      workspace_id = ANY(auth.user_workspace_ids())
      AND deleted_at IS NULL
      AND (
        NOT auth.is_workspace_guest(workspace_id)
        OR assignee_id = auth.uid()
      )
    )
    OR (
      -- Public project access (read-only, no guest restriction)
      public.is_public_project(project_id)
      AND deleted_at IS NULL
    )
  );

-- Notes are NOT accessible via public projects
-- (notes are team-internal thinking, not public-facing)
```

**Public Project Constraints**:
| Resource | Public Access | Rationale |
|----------|---------------|-----------|
| Project metadata | ✅ Read | Name, description, logo |
| Issues | ✅ Read | Public issue tracker view |
| Issue activities | ✅ Read | Public comment thread |
| Notes | ❌ None | Team-internal thinking |
| AI Context | ❌ None | Sensitive implementation details |
| Integrations | ❌ None | Security-sensitive |

---

## Role Hierarchy

Pilot Space implements four workspace roles:

| Role | Permissions |
|------|-------------|
| **owner** | Full access, can delete workspace, transfer ownership |
| **admin** | Manage members, all CRUD operations, configure integrations |
| **member** | Create/edit own content, view all workspace content |
| **guest** | Read-only access to assigned items only (see Guest Restrictions below) |

### Guest Role Restrictions

Guest users have limited access to protect workspace data:

| Resource | Guest Access |
|----------|--------------|
| **Issues** | View only issues assigned to them |
| **Notes** | No access (note content is team-internal) |
| **Activity Logs** | View only (if related to assigned issues) |
| **Integrations** | No access |
| **AI Configurations** | No access |
| **Workspace Members** | View only (names/roles) |

This is enforced at the database level via RLS policies using `auth.is_workspace_guest()`.

### Role Check Functions

```sql
-- Check if user is admin or owner
CREATE OR REPLACE FUNCTION auth.is_workspace_admin(ws_id uuid)
RETURNS boolean AS $$
  SELECT EXISTS (
    SELECT 1 FROM workspace_members
    WHERE user_id = auth.uid()
    AND workspace_id = ws_id
    AND role IN ('admin', 'owner')
  )
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- Check if user is owner
CREATE OR REPLACE FUNCTION auth.is_workspace_owner(ws_id uuid)
RETURNS boolean AS $$
  SELECT EXISTS (
    SELECT 1 FROM workspace_members
    WHERE user_id = auth.uid()
    AND workspace_id = ws_id
    AND role = 'owner'
  )
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- Check if user is guest (read-only access to assigned items only)
CREATE OR REPLACE FUNCTION auth.is_workspace_guest(ws_id uuid)
RETURNS boolean AS $$
  SELECT EXISTS (
    SELECT 1 FROM workspace_members
    WHERE user_id = auth.uid()
    AND workspace_id = ws_id
    AND role = 'guest'
  )
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- Check if user is a non-guest member (can create content)
CREATE OR REPLACE FUNCTION auth.is_content_creator(ws_id uuid)
RETURNS boolean AS $$
  SELECT EXISTS (
    SELECT 1 FROM workspace_members
    WHERE user_id = auth.uid()
    AND workspace_id = ws_id
    AND role IN ('owner', 'admin', 'member')
  )
$$ LANGUAGE sql SECURITY DEFINER STABLE;
```

---

## Soft Delete Patterns

### Soft Delete with RLS

```sql
-- All queries automatically exclude soft-deleted rows
CREATE POLICY "Exclude soft-deleted rows"
  ON issues FOR SELECT
  USING (deleted_at IS NULL);

-- Soft delete is an UPDATE, not DELETE
CREATE OR REPLACE FUNCTION soft_delete_issue(issue_id uuid)
RETURNS void AS $$
  UPDATE issues
  SET deleted_at = now(),
      deleted_by_id = auth.uid()
  WHERE id = issue_id
  AND (
    created_by_id = auth.uid()
    OR auth.is_workspace_admin(workspace_id)
  );
$$ LANGUAGE sql SECURITY DEFINER;
```

### Restore Soft-Deleted Items

```sql
-- Only creator or admin/owner can restore (per spec clarification)
CREATE OR REPLACE FUNCTION restore_issue(issue_id uuid)
RETURNS void AS $$
  UPDATE issues
  SET deleted_at = NULL,
      deleted_by_id = NULL
  WHERE id = issue_id
  AND deleted_at IS NOT NULL
  AND deleted_at > now() - interval '30 days'  -- 30-day restore window
  AND (
    created_by_id = auth.uid()
    OR auth.is_workspace_admin(workspace_id)
  );
$$ LANGUAGE sql SECURITY DEFINER;
```

---

## AI Task Queue RLS

The AI task queue uses service role only (not user-accessible):

```sql
-- AI task queue: service role only
ALTER TABLE ai_task_queue ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access"
  ON ai_task_queue
  USING (auth.role() = 'service_role');

-- No policies for anon or authenticated roles
-- This ensures only backend services can access the queue
```

---

## Integration Data RLS

Sensitive integration data (API keys, tokens) has stricter policies:

```sql
-- Integrations: Only admin/owner can view/modify
CREATE POLICY "Admins can manage integrations"
  ON integrations FOR ALL
  USING (
    auth.is_workspace_admin(workspace_id)
  )
  WITH CHECK (
    auth.is_workspace_admin(workspace_id)
  );

-- AI configurations: Only admin/owner
CREATE POLICY "Admins can manage AI config"
  ON ai_configurations FOR ALL
  USING (
    auth.is_workspace_admin(workspace_id)
  );
```

---

## Activity Logs RLS

Activity logs are append-only and viewable by all workspace members:

```sql
-- Activity logs: Members can view, system can insert
CREATE POLICY "Members can view activity"
  ON activity_logs FOR SELECT
  USING (
    workspace_id = ANY(auth.user_workspace_ids())
  );

-- Only system/service role can insert activities
CREATE POLICY "System can insert activity"
  ON activity_logs FOR INSERT
  WITH CHECK (
    auth.role() = 'service_role'
    OR (
      auth.workspace_role(workspace_id) IS NOT NULL
      AND user_id = auth.uid()
    )
  );

-- No UPDATE or DELETE allowed
-- Activity logs are immutable
```

---

## Embeddings Table RLS

Vector embeddings used for RAG search require workspace isolation:

```sql
-- Enable RLS on embeddings table
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;

-- SELECT: Workspace members can view embeddings (for search)
-- Guests cannot access embeddings (no search capability)
CREATE POLICY "Members can view workspace embeddings"
  ON embeddings FOR SELECT
  USING (
    workspace_id = ANY(auth.user_workspace_ids())
    AND NOT auth.is_workspace_guest(workspace_id)
  );

-- INSERT: Only service role can create embeddings
-- Embeddings are generated by background jobs, not user actions
CREATE POLICY "Service role can create embeddings"
  ON embeddings FOR INSERT
  WITH CHECK (
    auth.role() = 'service_role'
  );

-- UPDATE: Only service role can update embeddings
-- Embeddings are regenerated when content changes significantly
CREATE POLICY "Service role can update embeddings"
  ON embeddings FOR UPDATE
  USING (
    auth.role() = 'service_role'
  );

-- DELETE: Only service role can delete embeddings
-- Cleanup happens when source content is deleted
CREATE POLICY "Service role can delete embeddings"
  ON embeddings FOR DELETE
  USING (
    auth.role() = 'service_role'
  );
```

---

## Performance Optimization

### Index Strategies for RLS

```sql
-- Index for workspace_id filtering (all user-data tables)
CREATE INDEX idx_issues_workspace_id ON issues(workspace_id)
  WHERE deleted_at IS NULL;

CREATE INDEX idx_notes_workspace_id ON notes(workspace_id)
  WHERE deleted_at IS NULL;

-- Index for user membership lookup
CREATE INDEX idx_workspace_members_user_id
  ON workspace_members(user_id);

CREATE INDEX idx_workspace_members_workspace_role
  ON workspace_members(workspace_id, role);

-- Composite index for common query patterns
CREATE INDEX idx_issues_workspace_assignee
  ON issues(workspace_id, assignee_id)
  WHERE deleted_at IS NULL;
```

### Caching Helper Functions

```sql
-- Cache workspace IDs in session (per-transaction)
CREATE OR REPLACE FUNCTION auth.user_workspace_ids()
RETURNS uuid[] AS $$
DECLARE
  ws_ids uuid[];
BEGIN
  -- Check if already cached in session
  ws_ids := current_setting('app.user_workspace_ids', true)::uuid[];

  IF ws_ids IS NULL THEN
    SELECT ARRAY_AGG(workspace_id) INTO ws_ids
    FROM workspace_members
    WHERE user_id = auth.uid();

    -- Cache for this transaction
    PERFORM set_config('app.user_workspace_ids', ws_ids::text, true);
  END IF;

  RETURN ws_ids;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;
```

---

## Testing RLS Policies

### Test Setup

```sql
-- Create test users
INSERT INTO auth.users (id, email) VALUES
  ('user-1', 'owner@example.com'),
  ('user-2', 'member@example.com'),
  ('user-3', 'guest@example.com'),
  ('user-4', 'outsider@example.com');

-- Create test workspace
INSERT INTO workspaces (id, name) VALUES
  ('ws-1', 'Test Workspace');

-- Assign roles
INSERT INTO workspace_members (workspace_id, user_id, role) VALUES
  ('ws-1', 'user-1', 'owner'),
  ('ws-1', 'user-2', 'member'),
  ('ws-1', 'user-3', 'guest');

-- Create test issue
INSERT INTO issues (id, workspace_id, title, created_by_id) VALUES
  ('issue-1', 'ws-1', 'Test Issue', 'user-1');
```

### Test Cases

```sql
-- Test 1: Owner can see issue
SET LOCAL ROLE authenticated;
SET LOCAL request.jwt.claims = '{"sub": "user-1"}';
SELECT * FROM issues WHERE id = 'issue-1';
-- Expected: 1 row

-- Test 2: Member can see issue
SET LOCAL request.jwt.claims = '{"sub": "user-2"}';
SELECT * FROM issues WHERE id = 'issue-1';
-- Expected: 1 row

-- Test 3: Guest CANNOT see issue (not assigned to them)
SET LOCAL request.jwt.claims = '{"sub": "user-3"}';
SELECT * FROM issues WHERE id = 'issue-1';
-- Expected: 0 rows (guest can only view assigned issues)

-- Test 4: Outsider cannot see issue
SET LOCAL request.jwt.claims = '{"sub": "user-4"}';
SELECT * FROM issues WHERE id = 'issue-1';
-- Expected: 0 rows

-- Test 5: Member can create issue
SET LOCAL request.jwt.claims = '{"sub": "user-2"}';
INSERT INTO issues (workspace_id, title, created_by_id)
VALUES ('ws-1', 'Member Issue', 'user-2');
-- Expected: Success

-- Test 6: Guest cannot create issue
SET LOCAL request.jwt.claims = '{"sub": "user-3"}';
INSERT INTO issues (workspace_id, title, created_by_id)
VALUES ('ws-1', 'Guest Issue', 'user-3');
-- Expected: Error (policy violation)

-- Test 7: Outsider cannot create issue
SET LOCAL request.jwt.claims = '{"sub": "user-4"}';
INSERT INTO issues (workspace_id, title, created_by_id)
VALUES ('ws-1', 'Outsider Issue', 'user-4');
-- Expected: Error (policy violation)
```

---

## Common Pitfalls

### 1. Forgetting to Enable RLS

```sql
-- WRONG: Table without RLS
CREATE TABLE sensitive_data (...);
-- All users can see all data!

-- CORRECT: Always enable RLS
CREATE TABLE sensitive_data (...);
ALTER TABLE sensitive_data ENABLE ROW LEVEL SECURITY;
```

### 2. Using anon Key for Sensitive Operations

```typescript
// WRONG: Client using anon key for admin operations
const supabase = createClient(url, anonKey);
await supabase.from('integrations').select('*'); // Will fail

// CORRECT: Use service role on backend only
const supabase = createClient(url, serviceRoleKey);
```

### 3. Not Testing Policy Combinations

```sql
-- Policies are ANDed for restrictive, ORed for permissive
-- Make sure to test all role combinations
```

### 4. Expensive Policy Functions

```sql
-- WRONG: Subquery in every row check
CREATE POLICY "check_membership"
  ON issues FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM workspace_members
      WHERE user_id = auth.uid()
      AND workspace_id = issues.workspace_id
    )
  );

-- BETTER: Use pre-computed array
CREATE POLICY "check_membership"
  ON issues FOR SELECT
  USING (
    workspace_id = ANY(auth.user_workspace_ids())
  );
```

---

## Migration Checklist

When adding a new table:

- [ ] Enable RLS: `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
- [ ] Add workspace_id column (if user data)
- [ ] Create SELECT policy with workspace isolation
- [ ] Create INSERT policy with role check
- [ ] Create UPDATE policy with ownership/role check
- [ ] Create soft-delete policy (UPDATE, not DELETE)
- [ ] Add workspace_id index with deleted_at filter
- [ ] Test with all roles (owner, admin, member, guest, outsider)
- [ ] Verify guest access restrictions (assigned items only)
- [ ] Document in this file

**Special Tables (service role only):**
- `ai_task_queue` - Backend job processing only
- `embeddings` - Generated by background jobs, users can read (non-guests)
- `activity_logs` - Append-only, users can read, system inserts

---

## Related Documents

- [Infrastructure](./infrastructure.md) - Supabase setup
- [Supabase Integration](./supabase-integration.md) - Platform details
- [Backend Architecture](./backend-architecture.md) - Repository patterns
- [Data Model](../../specs/001-pilot-space-mvp/data-model.md) - Entity definitions
- [Constitution](../../.specify/memory/constitution.md) - Security principles

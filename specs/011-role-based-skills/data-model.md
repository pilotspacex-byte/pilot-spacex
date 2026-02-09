# Data Model: Role-Based Skills

**Feature**: 011-role-based-skills
**Created**: 2026-02-06

---

## Entity Relationship Diagram

```
User (existing)
├── 1:N → UserRoleSkill (per workspace)
├── 1:N → WorkspaceMember (per workspace)
└── default_sdlc_role (new field)

Workspace (existing)
├── 1:N → UserRoleSkill
├── 1:N → WorkspaceMember
├── 1:1 → WorkspaceOnboarding (steps JSONB extended)
└── 1:N → WorkspaceInvitation
              └── suggested_sdlc_role (new field)

RoleTemplate (new, seed data)
└── Referenced by UserRoleSkill.role_type
```

---

## New Tables

### user_role_skills

**Purpose**: Stores personalized AI skill descriptions per user-workspace pair. Each record represents one SDLC role the user holds in a specific workspace, along with the SKILL.md-format content that gets injected into the PilotSpace Agent.

**Source**: FR-002, FR-005, FR-013, FR-015

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, gen_random_uuid() | |
| user_id | UUID | FK users.id ON DELETE CASCADE, NOT NULL | Skill owner |
| workspace_id | UUID | FK workspaces.id ON DELETE CASCADE, NOT NULL | Workspace scope |
| role_type | VARCHAR(50) | NOT NULL | Predefined enum key (e.g., 'developer') or 'custom' |
| role_name | VARCHAR(100) | NOT NULL | Display name (e.g., "Senior QA Engineer") |
| skill_content | TEXT | NOT NULL | SKILL.md markdown content with YAML frontmatter |
| experience_description | TEXT | NULL | User's natural language input used for AI generation |
| is_primary | BOOLEAN | NOT NULL, DEFAULT FALSE | Primary role flag (one per user-workspace) |
| template_version | INTEGER | NULL | Tracks which version of RoleTemplate was used |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Auto-updated on modification |

**Constraints**:
- UNIQUE (user_id, workspace_id, role_type) — prevents duplicate role types
- CHECK (char_length(skill_content) <= 15000) — enforces ~2000 word cap
- CHECK (char_length(role_name) <= 100)

**Indexes**:
- `ix_user_role_skills_user_workspace` (user_id, workspace_id) — primary query pattern
- `ix_user_role_skills_workspace` (workspace_id) — workspace-level admin queries

**RLS Policies**:

```sql
-- Users can read their own skills + admins can read all in workspace
CREATE POLICY "user_role_skills_select" ON user_role_skills
FOR SELECT USING (
    user_id = auth.uid()
    OR workspace_id IN (
        SELECT wm.workspace_id FROM workspace_members wm
        WHERE wm.user_id = auth.uid()
        AND wm.role IN ('owner', 'admin')
    )
);

-- Users can modify only their own skills (not guests)
CREATE POLICY "user_role_skills_modify" ON user_role_skills
FOR ALL USING (
    user_id = auth.uid()
    AND workspace_id IN (
        SELECT wm.workspace_id FROM workspace_members wm
        WHERE wm.user_id = auth.uid()
        AND wm.role IN ('owner', 'admin', 'member')
    )
);
```

---

### role_templates

**Purpose**: Predefined SDLC role templates with default skill content. Seeded via migration. Read-only for application users.

**Source**: FR-001, FR-004, FR-017

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, gen_random_uuid() | |
| role_type | VARCHAR(50) | UNIQUE, NOT NULL | Enum key (e.g., 'developer', 'tester') |
| display_name | VARCHAR(100) | NOT NULL | Human-readable (e.g., "Developer") |
| description | TEXT | NOT NULL | Brief description for role selection UI |
| default_skill_content | TEXT | NOT NULL | Default SKILL.md content |
| icon | VARCHAR(50) | NOT NULL | Frontend icon identifier |
| sort_order | INTEGER | NOT NULL | Display ordering |
| version | INTEGER | NOT NULL, DEFAULT 1 | Template versioning for update notifications |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**RLS Policies**:

```sql
-- All authenticated users can read templates
CREATE POLICY "role_templates_select" ON role_templates
FOR SELECT USING (auth.uid() IS NOT NULL);
```

**Seed Data** (8 predefined templates):

| role_type | display_name | icon | sort_order |
|-----------|-------------|------|------------|
| business_analyst | Business Analyst | FileSearch | 1 |
| product_owner | Product Owner | Target | 2 |
| developer | Developer | Code | 3 |
| tester | Tester | TestTube | 4 |
| architect | Architect | Layers | 5 |
| tech_lead | Tech Lead | GitBranch | 6 |
| project_manager | Project Manager | GanttChart | 7 |
| devops | DevOps | Container | 8 |

---

## Extended Tables

### users (add column)

**Source**: FR-011

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| default_sdlc_role | VARCHAR(50) | NULL | Default role for new workspace joins. Matches role_type values. |

No RLS change needed — existing user policies apply.

### workspace_invitations (add column)

**Source**: FR-012

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| suggested_sdlc_role | VARCHAR(50) | NULL | Owner's role hint for invitee. Matches role_type values. |

No RLS change needed — existing invitation policies apply.

### workspace_onboardings (JSONB extension)

**Source**: FR-001

The `steps` JSONB field gains a new key `role_setup`. No schema change needed.

**Before**: `{"ai_providers": false, "invite_members": false, "first_note": false}`
**After**: `{"ai_providers": false, "invite_members": false, "first_note": false, "role_setup": false}`

Service-level change: `completion_percentage` calculation updates from dividing by 3 to dividing by 4.

---

## Migration Plan

**Migration**: `025_add_role_based_skills.py`
**Revises**: `024_enhanced_mcp_models`

**Upgrade steps**:
1. Create `role_templates` table
2. Create `user_role_skills` table with FK constraints
3. Add `default_sdlc_role` column to `users`
4. Add `suggested_sdlc_role` column to `workspace_invitations`
5. Create indexes
6. Enable RLS on both new tables
7. Create RLS policies
8. Seed `role_templates` with 8 predefined templates (content loaded from `ai/templates/role_templates/`)
9. Update existing `workspace_onboardings.steps` JSONB to include `role_setup: false`

**Downgrade steps**:
1. Drop RLS policies
2. Drop indexes
3. Drop `suggested_sdlc_role` from `workspace_invitations`
4. Drop `default_sdlc_role` from `users`
5. Drop `user_role_skills` table
6. Drop `role_templates` table
7. Remove `role_setup` key from existing `workspace_onboardings.steps` JSONB

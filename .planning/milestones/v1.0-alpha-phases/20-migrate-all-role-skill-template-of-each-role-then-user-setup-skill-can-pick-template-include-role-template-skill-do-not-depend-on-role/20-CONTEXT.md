# Phase 20: Skill Template Catalog - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Decouple skills from roles. Migrate existing role-based skills (RoleTemplate, UserRoleSkill, WorkspaceRoleSkill) into a unified skill template catalog. Users browse the catalog and pick templates — AI auto-personalizes the skill based on the template + user's experience. Skills no longer depend on `role_type` as a primary key; role-originated templates become one source among many.

This phase does NOT include: plugin system changes (Phase 19 plugins stay as-is), community template sharing across workspaces, or a built-in template editor with live preview.

</domain>

<decisions>
## Implementation Decisions

### Template Catalog Model (Claude's Decision)
- **Single unified `skill_templates` table** replaces both `RoleTemplate` and `WorkspaceRoleSkill` as the template source
- Each template has a `source` enum: `built_in` (migrated from RoleTemplate), `workspace` (admin-created, migrated from WorkspaceRoleSkill), `custom` (future)
- `role_type` becomes **optional metadata** on the template (nullable) — preserves lineage for migrated role templates but is not a primary key
- Template fields: `name`, `description`, `skill_content` (the template text), `icon`, `sort_order`, `source`, `role_type` (nullable), `is_active`, `created_by` (nullable)
- Templates are **workspace-scoped** (workspace_id FK) — built-in templates are seeded per workspace at creation (same pattern as plugin seeding from Phase 19)
- **Rationale:** Single table is simpler to query, avoids merging two data sources in the frontend, and the `source` field preserves provenance

### User Skill Selection Flow
- All workspace members can browse the skill template catalog
- User picks a template → AI auto-generates a personalized skill using the template content + user's experience description (same AI generation pattern as Phase 16 role skill wizard)
- Users can have **multiple active skills simultaneously** — all are materialized and injected into the AI agent
- User's personalized skills stored in a new `user_skills` table (replaces `user_role_skills`):
  - `user_id`, `workspace_id`, `template_id` (FK to skill_templates, nullable — allows skills without a template origin), `skill_content`, `experience_description`, `is_active`
  - No `role_type` column — skill identity comes from the template, not from a role
  - No `is_primary` — all active skills are equal (multiple active)

### Migration Strategy (Claude's Decision)
- **Additive migration, then deprecation:**
  1. Create `skill_templates` table and `user_skills` table
  2. Data migration: copy `RoleTemplate` rows → `skill_templates` (source=built_in), copy active `WorkspaceRoleSkill` rows → `skill_templates` (source=workspace)
  3. Data migration: copy `UserRoleSkill` rows → `user_skills` with `template_id` linked to the matching skill_template by `role_type`
  4. Update materializer to read from `user_skills` + `skill_templates` instead of `UserRoleSkill` + `WorkspaceRoleSkill`
  5. Old tables (`user_role_skills`, `workspace_role_skills`, `role_templates`) are **not dropped** in this phase — marked deprecated, queries removed
- **Rationale:** Additive approach is safer — old data stays intact, rollback is trivial (re-point materializer to old tables)

### Admin Template Management
- **Replace** the Phase 16 role-based "Generate Skill" wizard with a new "Create Template" flow
- Admin flow: Create Template → fill name, description, optional role association, experience prompt → AI generates template content → admin reviews → save to `skill_templates`
- Admins can edit/deactivate/delete workspace templates
- Built-in templates (migrated from RoleTemplate) are **read-only** for admins — they can deactivate but not edit built-in content
- Existing Phase 16 WorkspaceRoleSkill entries become workspace templates in the catalog automatically via migration

### Materializer Changes (Claude's Decision)
- `materialize_role_skills()` refactored → `materialize_skills()`:
  - Reads from `user_skills` (all active skills for the user in this workspace)
  - Falls back to workspace-level `skill_templates` where user has no personalized version (same precedence concept as WRSKL-03/04, but template-based)
  - Plugin skills from Phase 19 continue to be materialized separately (no change)
- Skill directory naming changes from `role-{role_type}/` to `skill-{template_id_short}/` or `skill-{sanitized_name}/`
- **Rationale:** Keeps the same materializer pattern but removes role_type coupling

### Frontend UI (Claude's Decision)
- Settings → Skills page restructured:
  - **"My Skills"** section: user's active personalized skills (cards with name, source template, edit/deactivate actions)
  - **"Skill Templates"** section: browsable catalog of workspace templates (cards with name, description, source badge, "Use This" button)
  - **Admin section** (admin only): "Create Template" button, manage workspace templates
- Remove the "Generate Skill" wizard from Phase 16 — replaced by the template-based flow
- Card layout consistent with plugin cards from Phase 19

### Claude's Discretion
- Exact Alembic migration file structure and sequencing
- Template card visual design details (spacing, badges, colors)
- AI generation prompt template for personalizing skills from templates
- Sanitization approach for skill directory names
- Whether to add a "preview" step before AI generation or go straight to generation
- Error handling for AI generation failures during template personalization
- Exact API endpoint paths and Pydantic schema field names

</decisions>

<specifics>
## Specific Ideas

- User said "skill do not depend on role" — this is the core constraint: `role_type` must not be a required field anywhere in the new system
- User wants step-by-step transparent decisions — all Claude decisions are documented above with rationale
- The existing Phase 16 "Generate Skill" flow is replaced, not kept alongside
- Multiple active skills simultaneously — no primary/secondary distinction

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RoleTemplate` model (`user_role_skill.py`): has `display_name`, `description`, `default_skill_content`, `icon`, `sort_order`, `version` — good template for the new `skill_templates` table
- `WorkspaceRoleSkill` model: has `skill_content`, `experience_description`, `is_active`, `created_by` — fields needed in the new template model
- `UserRoleSkill` model: has `user_id`, `skill_content`, `experience_description`, `is_primary`, `template_version` — migration source for `user_skills`
- `role_skill_materializer.py`: `materialize_role_skills()` + `_write_skill_file()` + `_build_frontmatter()` — refactor target, keep the file I/O pattern
- `GenerateRoleSkillService` (Phase 16): AI generation logic — reuse for template personalization
- Plugin card components (Phase 19): card layout pattern for the template catalog UI

### Established Patterns
- Workspace-scoped models with `WorkspaceScopedModel` base class
- Soft delete via `SoftDeleteMixin` + partial unique indexes (WHERE is_deleted = false)
- `encrypt_api_key()` / `decrypt_api_key()` for sensitive data (not needed here but pattern reference)
- Factory-based repositories (not DI container) for lightweight services — follow for template repository
- MobX stores for settings pages — create SkillTemplateStore following AISettingsStore pattern

### Integration Points
- `role_skill_materializer.py` line 28: `materialize_role_skills()` — primary refactor target
- `pilotspace_agent.py` line 289: calls materializer — interface must stay compatible
- Skills settings page: `frontend/src/app/(workspace)/[workspaceSlug]/skills/page.tsx` — restructure UI
- Workspace creation flow: seed built-in templates (same as plugin seeding pattern)
- `RoleSkillRepository` / `WorkspaceRoleSkillRepository` — replace with new repositories

</code_context>

<deferred>
## Deferred Ideas

- Cross-workspace template sharing (org-level template library) — requires org data model
- Template versioning with diff view (see what changed between versions) — future enhancement
- AI-suggested templates based on user's GitHub profile / activity — future phase
- Template marketplace / community sharing — separate phase
- Built-in template editor with live preview — future phase

</deferred>

---

*Phase: 20-skill-template-catalog*
*Context gathered: 2026-03-11*

# Phase 20: Skill Template Catalog - Research

**Researched:** 2026-03-11
**Domain:** Database migration, backend service refactoring, frontend UI restructuring
**Confidence:** HIGH

## Summary

Phase 20 decouples skills from roles by introducing a unified `skill_templates` table and `user_skills` table, replacing the current `RoleTemplate` + `UserRoleSkill` + `WorkspaceRoleSkill` triple-table system. The migration is additive (old tables remain, queries are redirected). The existing codebase has well-established patterns for every aspect of this work: workspace-scoped models (`WorkspaceScopedModel`), soft-delete with partial unique indexes, materializer file I/O, CQRS-lite services, factory-based repositories, and TanStack Query + observer frontend patterns.

The codebase is mature with 76 Alembic migrations, consistent patterns across all layers, and the Phase 20 commit (c3d2b3f5) already renamed `role-` prefixes to `skill-` in the materializer and unified the frontend SkillGeneratorModal. This phase builds directly on that foundation.

**Primary recommendation:** Execute as a 4-wave migration: (1) new tables + data migration, (2) backend services + materializer refactor, (3) API endpoints + frontend catalog UI, (4) deprecate old code paths and cleanup.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Single unified `skill_templates` table** replaces both `RoleTemplate` and `WorkspaceRoleSkill` as the template source
- Each template has a `source` enum: `built_in`, `workspace`, `custom` (future)
- `role_type` becomes **optional metadata** (nullable) -- preserves lineage but is not a primary key
- Template fields: `name`, `description`, `skill_content`, `icon`, `sort_order`, `source`, `role_type` (nullable), `is_active`, `created_by` (nullable)
- Templates are **workspace-scoped** (workspace_id FK) -- built-in templates seeded per workspace at creation
- **User Skill Selection Flow**: browse catalog, pick template, AI auto-generates personalized skill
- Users can have **multiple active skills simultaneously** -- all materialized and injected
- New `user_skills` table replaces `user_role_skills`: `user_id`, `workspace_id`, `template_id` (FK, nullable), `skill_content`, `experience_description`, `is_active` -- no `role_type`, no `is_primary`
- **Additive migration, then deprecation**: old tables not dropped, queries removed
- **Replace** Phase 16 "Generate Skill" wizard with "Create Template" flow
- Built-in templates are **read-only** for admins (deactivate but not edit)
- Materializer refactored: `materialize_role_skills()` -> `materialize_skills()` reading from `user_skills`
- Skill directory naming: `skill-{template_id_short}/` or `skill-{sanitized_name}/`
- Frontend: "My Skills" + "Skill Templates" + admin "Create Template" sections

### Claude's Discretion
- Exact Alembic migration file structure and sequencing
- Template card visual design details (spacing, badges, colors)
- AI generation prompt template for personalizing skills from templates
- Sanitization approach for skill directory names
- Whether to add a "preview" step before AI generation or go straight to generation
- Error handling for AI generation failures during template personalization
- Exact API endpoint paths and Pydantic schema field names

### Deferred Ideas (OUT OF SCOPE)
- Cross-workspace template sharing (org-level template library)
- Template versioning with diff view
- AI-suggested templates based on user's GitHub profile/activity
- Template marketplace/community sharing
- Built-in template editor with live preview
</user_constraints>

## Architecture Patterns

### Current System (Being Replaced)

```
role_templates (global, no workspace_id)
  |-- role_type (PK-like, unique)
  |-- display_name, description, default_skill_content, icon, sort_order, version

user_role_skills (WorkspaceScopedModel)
  |-- user_id, workspace_id, role_type, role_name
  |-- skill_content, experience_description, is_primary, template_version
  |-- UNIQUE(user_id, workspace_id, role_type)

workspace_role_skills (WorkspaceScopedModel)
  |-- workspace_id, role_type, role_name
  |-- skill_content, experience_description, is_active, created_by
  |-- PARTIAL UNIQUE(workspace_id, role_type) WHERE is_deleted = false
```

### Target System

```
skill_templates (WorkspaceScopedModel)
  |-- workspace_id (FK)
  |-- name VARCHAR(100) NOT NULL
  |-- description TEXT NOT NULL
  |-- skill_content TEXT NOT NULL (max 15000)
  |-- icon VARCHAR(50) NOT NULL DEFAULT 'Wand2'
  |-- sort_order INTEGER NOT NULL DEFAULT 0
  |-- source VARCHAR(20) NOT NULL  -- 'built_in' | 'workspace' | 'custom'
  |-- role_type VARCHAR(50) NULL  -- optional lineage
  |-- is_active BOOLEAN NOT NULL DEFAULT true
  |-- created_by UUID NULL FK -> users.id (SET NULL)
  |-- PARTIAL UNIQUE(workspace_id, name) WHERE is_deleted = false
  |-- INDEX(workspace_id, source)
  |-- INDEX(workspace_id, is_active)

user_skills (WorkspaceScopedModel)
  |-- user_id UUID NOT NULL FK -> users.id (CASCADE)
  |-- workspace_id (from WorkspaceScopedModel)
  |-- template_id UUID NULL FK -> skill_templates.id (SET NULL)
  |-- skill_content TEXT NOT NULL (max 15000)
  |-- experience_description TEXT NULL
  |-- is_active BOOLEAN NOT NULL DEFAULT true
  |-- PARTIAL UNIQUE(user_id, workspace_id, template_id) WHERE is_deleted = false
  |-- INDEX(user_id, workspace_id)
  |-- INDEX(workspace_id)
```

### Materializer Flow (New)

```
materialize_skills(db_session, user_id, workspace_id, skills_dir)
  1. Load user's active user_skills (is_active=true, is_deleted=false)
  2. For each user_skill:
     - dir_name = skill-{sanitized_name(template.name or skill.id[:8])}
     - Write SKILL.md with frontmatter
  3. Load workspace skill_templates where user has NO matching user_skill
     (fallback for templates without personalization)
  4. For each fallback template:
     - dir_name = skill-{sanitized_name(template.name)}
     - Write SKILL.md with workspace origin marker
  5. Clean stale skill-* dirs
  6. Continue with materialize_plugin_skills (unchanged)
```

### Recommended Project Structure (New Files)

```
backend/src/pilot_space/
  infrastructure/database/models/
    skill_template.py           # SkillTemplate model
    user_skill.py               # UserSkill model
  infrastructure/database/repositories/
    skill_template_repository.py  # SkillTemplateRepository
    user_skill_repository.py      # UserSkillRepository
  application/services/
    skill_template/
      __init__.py
      types.py
      create_template_service.py
      list_templates_service.py
      update_template_service.py
      delete_template_service.py
      seed_templates_service.py    # Seed built-in templates on workspace creation
    user_skill/
      __init__.py
      types.py
      create_user_skill_service.py   # Pick template -> AI personalize -> save
      list_user_skills_service.py
      update_user_skill_service.py
      delete_user_skill_service.py
  api/v1/
    schemas/
      skill_template.py
      user_skill.py
    routers/
      skill_templates.py
      user_skills.py
  ai/agents/
    role_skill_materializer.py  # Refactored in-place (keep filename or rename)

backend/alembic/versions/
  077_add_skill_templates_and_user_skills.py  # Schema + data migration

frontend/src/
  services/api/
    skill-templates.ts          # TanStack Query hooks
    user-skills.ts              # TanStack Query hooks (replaces role-skills partially)
  features/settings/
    components/
      template-catalog.tsx      # Browsable template grid
      template-card.tsx         # Single template card with "Use This" button
      my-skill-card.tsx         # User's active skill card
      create-template-modal.tsx # Admin modal for creating workspace templates
    pages/
      skills-settings-page.tsx  # Restructured with My Skills + Catalog sections
```

### Data Migration Strategy

The Alembic migration (077) must:

1. **Create `skill_templates` table** with all columns, indexes, RLS policies
2. **Create `user_skills` table** with all columns, indexes, RLS policies
3. **Migrate data** using raw SQL within the migration:

```python
# Migrate RoleTemplate -> skill_templates (per workspace)
# For each workspace, insert a copy of each role_template as source='built_in'
op.execute(text("""
    INSERT INTO skill_templates (id, workspace_id, name, description, skill_content,
        icon, sort_order, source, role_type, is_active, created_by,
        created_at, updated_at, is_deleted)
    SELECT
        gen_random_uuid(),
        wm.workspace_id,
        rt.display_name,
        rt.description,
        rt.default_skill_content,
        rt.icon,
        rt.sort_order,
        'built_in',
        rt.role_type,
        true,
        NULL,
        rt.created_at,
        rt.updated_at,
        false
    FROM role_templates rt
    CROSS JOIN (SELECT DISTINCT workspace_id FROM workspace_members) wm
"""))

# Migrate WorkspaceRoleSkill -> skill_templates (source='workspace')
op.execute(text("""
    INSERT INTO skill_templates (id, workspace_id, name, description, skill_content,
        icon, sort_order, source, role_type, is_active, created_by,
        created_at, updated_at, is_deleted, deleted_at)
    SELECT
        gen_random_uuid(),
        wrs.workspace_id,
        wrs.role_name,
        'Workspace skill for ' || wrs.role_type,
        wrs.skill_content,
        'Wand2',
        100,
        'workspace',
        wrs.role_type,
        wrs.is_active,
        wrs.created_by,
        wrs.created_at,
        wrs.updated_at,
        wrs.is_deleted,
        wrs.deleted_at
    FROM workspace_role_skills wrs
"""))

# Migrate UserRoleSkill -> user_skills
# Link template_id by matching role_type + workspace_id to skill_templates
op.execute(text("""
    INSERT INTO user_skills (id, user_id, workspace_id, template_id, skill_content,
        experience_description, is_active, created_at, updated_at, is_deleted, deleted_at)
    SELECT
        gen_random_uuid(),
        urs.user_id,
        urs.workspace_id,
        st.id,
        urs.skill_content,
        urs.experience_description,
        true,
        urs.created_at,
        urs.updated_at,
        urs.is_deleted,
        urs.deleted_at
    FROM user_role_skills urs
    LEFT JOIN skill_templates st
        ON st.workspace_id = urs.workspace_id
        AND st.role_type = urs.role_type
        AND st.source = 'built_in'
        AND st.is_deleted = false
"""))
```

**Critical:** Use `gen_random_uuid()` (PostgreSQL function) for new IDs. Use `LEFT JOIN` for template_id so user_skills with custom roles still migrate (template_id = NULL).

### Anti-Patterns to Avoid
- **Do NOT drop old tables in this migration** -- additive only, old data stays intact
- **Do NOT use Python ORM in migration** -- use raw SQL via `op.execute(text(...))` for data migration performance
- **Do NOT break the materializer call interface** -- `pilotspace_agent.py` is at 698 lines and calls `materialize_role_skills()` directly; keep the function name or update the single call site
- **Do NOT add workspace_id to `role_templates`** -- leave the old table untouched; new `skill_templates` is workspace-scoped

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Workspace-scoped model | Custom base class | `WorkspaceScopedModel` from `base.py` | Includes id, workspace_id, created_at, updated_at, is_deleted, deleted_at |
| Soft delete | Custom delete logic | `SoftDeleteMixin` (already in WorkspaceScopedModel) | Consistent with every other workspace entity |
| Unique constraints after delete | DELETE then INSERT | Partial unique index `WHERE is_deleted = false` | Established pattern from WorkspaceRoleSkill (migration 073) |
| RLS policies | Custom auth checks | `get_workspace_rls_policy_sql()` template from `rls.py` | Consistent RLS across all tables |
| Template seeding | Manual INSERT in workspace creation | `SeedTemplatesService` following `SeedPluginsService` pattern | Non-fatal, fire-and-forget via `asyncio.create_task` |
| AI skill generation | New generation service | Reuse `GenerateRoleSkillService` with modified prompt | Already handles retries, fallback, rate limiting |
| Frontend data fetching | Custom fetch | TanStack Query hooks following `workspace-role-skills.ts` pattern | Consistent with existing API layer |

## Common Pitfalls

### Pitfall 1: Migration Data Integrity
**What goes wrong:** Data migration creates orphaned or duplicate records if not carefully ordered.
**Why it happens:** `skill_templates` must exist before `user_skills` can reference them via template_id FK.
**How to avoid:** Migration steps must be ordered: (1) create skill_templates table, (2) migrate role_templates and workspace_role_skills into it, (3) create user_skills table, (4) migrate user_role_skills into it with template_id lookups.
**Warning signs:** FK constraint violations during migration.

### Pitfall 2: Materializer Interface Break
**What goes wrong:** `pilotspace_agent.py` (698 lines, at limit) calls `materialize_role_skills()` -- renaming breaks the agent.
**Why it happens:** Tight coupling between agent and materializer function name.
**How to avoid:** Either keep `materialize_role_skills` as a thin wrapper that calls new `materialize_skills`, or update the single call site in pilotspace_agent.py (line ~289). Prefer wrapper approach to avoid touching the 698-line file.
**Warning signs:** Agent fails to load skills silently.

### Pitfall 3: OperationalError Guard for Backward Compatibility
**What goes wrong:** Pre-migration environments crash when materializer queries new tables.
**Why it happens:** The materializer runs on every agent invocation, including during deployments before migration.
**How to avoid:** Wrap new table queries in `try/except OperationalError` guard, same pattern as existing workspace_role_skills query in materializer (line 84-93). Fall back to old queries if new tables don't exist.
**Warning signs:** 500 errors on agent invocation after deploy but before migration.

### Pitfall 4: Workspace Creation Seeding Race Condition
**What goes wrong:** New workspace created during migration has no built-in templates.
**Why it happens:** Migration seeds existing workspaces; new workspace creation must also seed.
**How to avoid:** Add template seeding to workspace creation flow (same pattern as `SeedPluginsService`), using `asyncio.create_task` for fire-and-forget non-blocking execution.
**Warning signs:** New workspaces have empty template catalog.

### Pitfall 5: Frontend Query Key Conflicts
**What goes wrong:** Old and new API hooks use conflicting TanStack Query cache keys, causing stale data.
**Why it happens:** If old `['workspace-role-skills']` and new `['skill-templates']` keys coexist.
**How to avoid:** New hooks use distinct query keys: `['skill-templates', workspaceId]`, `['user-skills', workspaceId]`. Old hooks remain but are gradually removed from UI.
**Warning signs:** Stale data or flashing between old/new state.

### Pitfall 6: CheckConstraint char_length vs length
**What goes wrong:** SQLite test DB fails on `char_length()` which is PostgreSQL-specific.
**Why it happens:** Existing Phase 16 decision (STATE.md): use `length()` not `char_length()` for ANSI SQL compatibility.
**How to avoid:** Use `length(skill_content) <= 15000` in CheckConstraints, consistent with WorkspaceRoleSkill model.
**Warning signs:** Test failures with "no such function: char_length".

### Pitfall 7: pilotspace_agent.py Line Limit
**What goes wrong:** Any modification to `pilotspace_agent.py` exceeds the 700-line pre-commit limit.
**Why it happens:** File is already 698 lines.
**How to avoid:** Keep materializer call as a simple import + function call. Do NOT add logic to the agent file. If refactoring materializer name, update the single call site only.
**Warning signs:** Pre-commit hook rejection.

## Code Examples

### New SkillTemplate Model

```python
# Source: follows WorkspaceRoleSkill pattern from workspace_role_skill.py
class SkillTemplate(WorkspaceScopedModel):
    __tablename__ = "skill_templates"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    skill_content: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("'Wand2'"))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # built_in | workspace | custom
    role_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        Index("uq_skill_templates_workspace_name", "workspace_id", "name",
              unique=True, postgresql_where=text("is_deleted = false")),
        Index("ix_skill_templates_workspace_source", "workspace_id", "source"),
        Index("ix_skill_templates_workspace_active", "workspace_id", "is_active"),
        CheckConstraint("length(skill_content) <= 15000", name="ck_skill_templates_content_length"),
        CheckConstraint("length(name) <= 100", name="ck_skill_templates_name_length"),
    )
```

### New UserSkill Model

```python
# Source: follows UserRoleSkill pattern from user_role_skill.py
class UserSkill(WorkspaceScopedModel):
    __tablename__ = "user_skills"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skill_templates.id", ondelete="SET NULL"), nullable=True
    )
    skill_content: Mapped[str] = mapped_column(Text, nullable=False)
    experience_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    # Relationships
    user: Mapped["User"] = relationship("User", lazy="joined")
    template: Mapped["SkillTemplate | None"] = relationship("SkillTemplate", lazy="joined")

    __table_args__ = (
        Index("uq_user_skills_user_workspace_template", "user_id", "workspace_id", "template_id",
              unique=True, postgresql_where=text("is_deleted = false")),
        Index("ix_user_skills_user_workspace", "user_id", "workspace_id"),
        Index("ix_user_skills_workspace", "workspace_id"),
        CheckConstraint("length(skill_content) <= 15000", name="ck_user_skills_content_length"),
    )
```

### Sanitized Directory Name for Materializer

```python
import re

def _sanitize_skill_dir_name(name: str, fallback_id: str) -> str:
    """Sanitize template name for filesystem directory.

    Examples:
        "Senior Developer" -> "skill-senior-developer"
        "My Custom!@# Skill" -> "skill-my-custom-skill"
        "" -> "skill-{fallback_id[:8]}"
    """
    sanitized = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not sanitized:
        sanitized = fallback_id[:8]
    return f"skill-{sanitized}"
```

### Template Seeding Service (follows SeedPluginsService)

```python
class SeedTemplatesService:
    """Seed built-in skill templates into new workspaces."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._session = db_session

    async def seed_workspace(self, workspace_id: UUID) -> None:
        """Copy all RoleTemplate rows into skill_templates for this workspace.

        Non-fatal: all exceptions logged, never propagated.
        """
        from pilot_space.infrastructure.database.repositories.role_skill_repository import (
            RoleTemplateRepository,
        )
        repo = RoleTemplateRepository(self._session)
        templates = await repo.get_all_ordered()

        template_repo = SkillTemplateRepository(self._session)
        for t in templates:
            await template_repo.create(
                workspace_id=workspace_id,
                name=t.display_name,
                description=t.description,
                skill_content=t.default_skill_content,
                icon=t.icon,
                sort_order=t.sort_order,
                source="built_in",
                role_type=t.role_type,
            )
```

### Refactored Materializer Core

```python
async def materialize_skills(
    db_session: AsyncSession,
    user_id: UUID,
    workspace_id: UUID,
    skills_dir: Path,
) -> int:
    """Write user's skills + workspace template fallbacks as SKILL.md files.

    New flow for Phase 20 — reads from user_skills and skill_templates.
    Falls back to old tables if new tables don't exist (OperationalError guard).
    """
    from sqlalchemy.exc import OperationalError

    try:
        return await _materialize_from_new_tables(db_session, user_id, workspace_id, skills_dir)
    except OperationalError:
        logger.debug("New skill tables not available, falling back to legacy materializer")
        return await _materialize_from_legacy_tables(db_session, user_id, workspace_id, skills_dir)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `role-{role_type}/` directories | `skill-{type}/` directories | Phase 20 commit c3d2b3f5 | Already deployed, legacy cleanup in materializer |
| Separate personal/workspace wizards | Unified `SkillGeneratorModal` | Phase 20 commit c3d2b3f5 | Single modal with mode toggle |
| `RoleTemplate` as global table | Will become workspace-scoped `skill_templates` | This phase | Per-workspace template catalog |
| `role_type` as primary identifier | `template_id` (nullable) as link | This phase | Skills decoupled from roles |
| Max 3 roles per user-workspace | Multiple active skills (no cap specified) | This phase | Consider adding a reasonable cap (e.g., 10) |

**Already completed in Phase 20 commit (c3d2b3f5):**
- Materializer renamed `role-` to `skill-` directory prefix
- Legacy `role-*` directory cleanup added
- Frontend SkillGeneratorModal unified personal/workspace flows
- UI text updated from "Role" to "Skill"
- `role_type`/`role_name` made optional in GenerateWorkspaceSkillRequest

## Existing Code Inventory (Files to Modify/Replace)

### Backend - To Deprecate (queries removed, tables kept)
| File | Lines | Action |
|------|-------|--------|
| `models/user_role_skill.py` | 176 | Keep model, stop importing in new code |
| `models/workspace_role_skill.py` | 103 | Keep model, stop importing in new code |
| `repositories/role_skill_repository.py` | 197 | Keep file, remove references from new services |
| `repositories/workspace_role_skill_repository.py` | 223 | Keep file, remove references from new services |
| `services/role_skill/` (entire package) | ~460 | Keep, old endpoints still work during transition |
| `services/workspace_role_skill/` (entire package) | ~200 | Keep, old endpoints still work during transition |
| `routers/role_skills.py` | 441 | Keep endpoints, add deprecation header |
| `routers/workspace_role_skills.py` | 308 | Keep endpoints, add deprecation header |

### Backend - To Refactor
| File | Lines | Action |
|------|-------|--------|
| `agents/role_skill_materializer.py` | 331 | Refactor to read from new tables (with OperationalError fallback) |
| `services/role_skill/types.py` | 24 | Keep VALID_ROLE_TYPES for backward compat |

### Frontend - To Refactor
| File | Lines | Action |
|------|-------|--------|
| `settings/pages/skills-settings-page.tsx` | 417 | Restructure: My Skills + Template Catalog |
| `settings/components/skill-generator-modal.tsx` | 557 | Adapt for template-based flow |
| `services/api/workspace-role-skills.ts` | 113 | Add deprecation, create new API services |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24+ |
| Config file | `backend/pyproject.toml` |
| Quick run command | `cd backend && uv run pytest tests/unit/ -x -q` |
| Full suite command | `cd backend && uv run pytest --cov` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| P20-01 | SkillTemplate model CRUD | unit | `cd backend && uv run pytest tests/unit/repositories/test_skill_template_repository.py -x` | Wave 0 |
| P20-02 | UserSkill model CRUD | unit | `cd backend && uv run pytest tests/unit/repositories/test_user_skill_repository.py -x` | Wave 0 |
| P20-03 | Data migration integrity | unit | `cd backend && uv run pytest tests/unit/migrations/test_077_migration.py -x` | Wave 0 |
| P20-04 | Materializer reads new tables | unit | `cd backend && uv run pytest tests/unit/ai/agents/test_role_skill_materializer.py -x` | Existing (update) |
| P20-05 | Template CRUD API endpoints | unit | `cd backend && uv run pytest tests/unit/routers/test_skill_templates_router.py -x` | Wave 0 |
| P20-06 | User skill API endpoints | unit | `cd backend && uv run pytest tests/unit/routers/test_user_skills_router.py -x` | Wave 0 |
| P20-07 | Template seeding on workspace creation | unit | `cd backend && uv run pytest tests/unit/services/test_seed_templates_service.py -x` | Wave 0 |
| P20-08 | AI personalization from template | unit | `cd backend && uv run pytest tests/unit/services/test_create_user_skill_service.py -x` | Wave 0 |
| P20-09 | Frontend template catalog renders | unit | `cd frontend && pnpm vitest run src/features/settings --reporter=verbose` | Update existing |
| P20-10 | Frontend user skill CRUD hooks | unit | `cd frontend && pnpm vitest run src/services/api/user-skills.test.ts` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest tests/unit/ -x -q`
- **Per wave merge:** `make quality-gates-backend && make quality-gates-frontend`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/repositories/test_skill_template_repository.py` -- covers P20-01
- [ ] `tests/unit/repositories/test_user_skill_repository.py` -- covers P20-02
- [ ] `tests/unit/services/test_seed_templates_service.py` -- covers P20-07
- [ ] `tests/unit/services/test_create_user_skill_service.py` -- covers P20-08
- [ ] `tests/unit/routers/test_skill_templates_router.py` -- covers P20-05
- [ ] `tests/unit/routers/test_user_skills_router.py` -- covers P20-06
- [ ] `frontend/src/services/api/user-skills.test.ts` -- covers P20-10

## Open Questions

1. **Max active skills per user-workspace**
   - What we know: Old system had MAX_ROLES_PER_USER_WORKSPACE = 3. New system says "multiple active skills simultaneously" with no cap.
   - What's unclear: Should there be a cap? Materializer performance degrades with many skills.
   - Recommendation: Set a reasonable default cap of 10 (configurable). Prevents abuse without limiting flexibility.

2. **Skill directory naming collision**
   - What we know: CONTEXT.md says `skill-{template_id_short}/` or `skill-{sanitized_name}/`.
   - What's unclear: If two templates have names that sanitize to the same string, directories collide.
   - Recommendation: Use `skill-{sanitized_name}-{id[:6]}/` to guarantee uniqueness while keeping human readability.

3. **Old API deprecation timeline**
   - What we know: Old endpoints remain functional, queries not removed.
   - What's unclear: When to actually remove old endpoints.
   - Recommendation: Add `Deprecation: true` header to old endpoints. Remove in a future cleanup phase (not this phase).

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis of all files listed in inventory
- `backend/src/pilot_space/infrastructure/database/models/user_role_skill.py` -- RoleTemplate + UserRoleSkill schemas
- `backend/src/pilot_space/infrastructure/database/models/workspace_role_skill.py` -- WorkspaceRoleSkill schema
- `backend/src/pilot_space/ai/agents/role_skill_materializer.py` -- current materializer (331 lines)
- `backend/src/pilot_space/application/services/role_skill/generate_role_skill_service.py` -- AI generation service (460 lines)
- `backend/alembic/versions/073_add_workspace_role_skills.py` -- migration pattern reference
- `backend/alembic/versions/026_add_role_based_skills.py` -- template seeding pattern reference
- `backend/src/pilot_space/application/services/workspace_plugin/seed_plugins_service.py` -- seeding pattern
- `frontend/src/features/settings/pages/skills-settings-page.tsx` -- current UI (417 lines)
- `frontend/src/services/api/workspace-role-skills.ts` -- current API hooks (113 lines)
- Git commit c3d2b3f5 -- Phase 20 renaming already completed

### Secondary (MEDIUM confidence)
- `backend/src/pilot_space/infrastructure/database/base.py` -- base model classes

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries and patterns already established in codebase
- Architecture: HIGH -- direct analysis of existing models, services, and materializer
- Pitfalls: HIGH -- drawn from actual codebase constraints (698-line agent, SQLite test guard, partial unique indexes)
- Migration strategy: HIGH -- follows established patterns from migrations 026 and 073

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable -- all patterns are internal codebase patterns)

# Phase 16: Workspace Role Skills - Research

**Researched:** 2026-03-10
**Domain:** AI skill inheritance, workspace admin settings, role-based access
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WRSKL-01 | Workspace admin writes a role description; AI generates a workspace-level skill for that role | Existing `GenerateRoleSkillService` reusable; new `WorkspaceRoleSkill` model + `pending` status needed |
| WRSKL-02 | Admin reviews and approves AI-generated skill before it becomes active for the workspace | Same review/approve pattern as `SkillGenerationWizard` (preview → accept); add `is_active` flag gate |
| WRSKL-03 | Members with a matching role automatically inherit the workspace-level skill | `materialize_role_skills` in agent stream is the injection point; extend to load workspace skills after user skills |
| WRSKL-04 | User's personal skill overrides workspace skill if both exist for the same role | Materialization precedence: user skill wins when `UserRoleSkill` exists for same `role_type`; workspace skill fills the gap otherwise |
</phase_requirements>

---

## Summary

Phase 16 introduces **workspace-level role skills**: an admin configures a skill for a workspace role (e.g., "developer"), the AI generates the content, the admin reviews it and explicitly activates it, and members whose `WorkspaceMember.role` matches the configured workspace role automatically have the skill injected into their AI sessions — unless they already have a personal `UserRoleSkill` for the same `role_type`.

The architecture already has all the building blocks. Personal skills exist as `UserRoleSkill` (per user-workspace-role). Workspace-level skills need a new model `WorkspaceRoleSkill` (per workspace-role, admin-owned) with an `is_active` boolean as the approval gate. The materialization layer (`role_skill_materializer.py`) already runs in every `PilotSpaceAgent.stream()` call and injects SKILL.md files into the SDK sandbox. Extending it to also inject workspace skills (only when no personal skill exists for the same role) satisfies WRSKL-03 and WRSKL-04 in a single change.

The frontend surface is the existing `/roles` page (`SkillsSettingsPage`). The current page shows only personal skills. Admins will get a new admin-only section (or a separate `/settings/workspace-roles` page) that shows workspace-level skill cards with an approval toggle. Non-admin members see the `/roles` page unchanged (their personal skills). No new route is strictly necessary — an admin section within the roles settings page keeps complexity low.

**Primary recommendation:** New `WorkspaceRoleSkill` model + migration 073; reuse `GenerateRoleSkillService`; add admin-only API routes under `/workspaces/{id}/workspace-role-skills`; extend `materialize_role_skills` to load workspace skills as fallback; admin UI section in the existing roles settings page.

---

## Standard Stack

### Core (same as existing skill system)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy async | existing | `WorkspaceRoleSkill` ORM model | All models use this pattern |
| Alembic | existing | Migration 073 for new table | Project migration standard |
| FastAPI | existing | New router `workspace_role_skills.py` | All routers use FastAPI |
| Pydantic v2 | existing | Request/response schemas | All schemas use Pydantic v2 |
| TanStack Query | existing | Frontend data fetching hooks | Settings module uses this |
| MobX | existing | Admin UI state | All settings pages use MobX stores |
| shadcn/ui | existing | Card, Button, Badge, Alert | Already in `SkillCard` pattern |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| dependency-injector | existing | DI wiring for new services | New services need container registration |
| asyncio.to_thread | stdlib | File I/O in materializer | Already used in `role_skill_materializer.py` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `is_active` flag on `WorkspaceRoleSkill` | Separate approval_status enum | Flag is simpler; the two states are pending (false) and active (true); no rejected/expired states needed for workspace skills |
| New `/settings/workspace-roles` route | Admin section in existing `/roles` page | Separate route adds navigation complexity; admin section within roles page reduces duplication and surface area |
| `role_type` key matching workspace member role | Separate `workspace_member_role` column | `role_type` is already the SDLC skill concept; workspace membership has `WorkspaceRole` (OWNER/ADMIN/MEMBER/GUEST); these are different dimensions — workspace role skill should be scoped to SDLC `role_type` not `WorkspaceRole` |

---

## Architecture Patterns

### Recommended Project Structure

```
backend/src/pilot_space/
├── infrastructure/database/
│   ├── models/workspace_role_skill.py        # NEW: WorkspaceRoleSkill model
│   ├── repositories/workspace_role_skill_repository.py  # NEW: CRUD + workspace queries
├── application/services/workspace_role_skill/  # NEW: service package
│   ├── __init__.py
│   ├── types.py                              # Payloads + shared types
│   ├── create_workspace_skill_service.py     # Admin create/generate
│   ├── activate_workspace_skill_service.py   # Admin approve → is_active=True
│   ├── list_workspace_skills_service.py      # List for admin view
│   ├── delete_workspace_skill_service.py     # Admin remove
├── api/v1/
│   ├── routers/workspace_role_skills.py      # NEW: admin-only endpoints
│   ├── schemas/workspace_role_skill.py       # NEW: request/response schemas
├── ai/agents/
│   └── role_skill_materializer.py            # EXTEND: load workspace skills as fallback

frontend/src/
├── services/api/workspace-role-skills.ts     # NEW: typed API client
├── features/settings/
│   ├── components/workspace-skill-card.tsx   # NEW: admin card with approve toggle
│   ├── pages/skills-settings-page.tsx        # EXTEND: admin section
├── stores/                                   # EXTEND: WorkspaceRoleSkillStore or inline
```

### Pattern 1: WorkspaceRoleSkill Model

**What:** Workspace-level skill, admin-owned, one per workspace per role_type. Separate from `UserRoleSkill` (which is per user-workspace-role).
**When to use:** Storing the admin-configured skill content awaiting or having received approval.

```python
# Source: modelled on UserRoleSkill in user_role_skill.py
class WorkspaceRoleSkill(WorkspaceScopedModel):
    __tablename__ = "workspace_role_skills"

    role_type: Mapped[str]          # matches VALID_ROLE_TYPES + "custom"
    role_name: Mapped[str]          # display name
    skill_content: Mapped[str]      # SKILL.md markdown content
    experience_description: Mapped[str | None]
    is_active: Mapped[bool]         # False = pending review, True = live
    created_by: Mapped[uuid.UUID]   # FK to users.id (the admin who created it)

    __table_args__ = (
        UniqueConstraint("workspace_id", "role_type",
                         name="uq_workspace_role_skills_workspace_role"),
        CheckConstraint("char_length(skill_content) <= 15000", ...),
        Index("ix_workspace_role_skills_workspace_active", "workspace_id", "is_active"),
    )
```

Key constraints:
- UNIQUE on `(workspace_id, role_type)` — one skill per workspace per role
- `is_active` is the approval gate (WRSKL-02)
- `created_by` FK allows auditing and permission checks

### Pattern 2: Materialization Extension (WRSKL-03, WRSKL-04)

**What:** Extend `materialize_role_skills()` to load active workspace skills as fallback when no personal skill exists for the same role_type.
**When to use:** Called in every `PilotSpaceAgent._build_stream_config()` — already the injection point.

```python
# Source: backend/src/pilot_space/ai/agents/role_skill_materializer.py
async def materialize_role_skills(
    db_session: AsyncSession,
    user_id: UUID,
    workspace_id: UUID,
    skills_dir: Path,
) -> int:
    # Step 1: Existing — load user's personal skills
    repo = RoleSkillRepository(db_session)
    user_skills = await repo.get_by_user_workspace(user_id, workspace_id)

    # NEW Step 2: Load active workspace skills, skip any role_type covered by user
    from pilot_space.infrastructure.database.repositories.workspace_role_skill_repository import (
        WorkspaceRoleSkillRepository,
    )
    user_role_types = {s.role_type for s in user_skills}
    ws_repo = WorkspaceRoleSkillRepository(db_session)
    workspace_skills = await ws_repo.get_active_by_workspace(workspace_id)
    inherited_skills = [s for s in workspace_skills if s.role_type not in user_role_types]

    # Write user skills (priority: primary first)
    # Write inherited workspace skills with frontmatter marking them workspace-origin
    # WRSKL-04: user skills already written → workspace skills only fill gaps
```

**Frontmatter for workspace-inherited skills:**
```yaml
---
name: role-{role_type}
description: "{role_name}" workspace role skill (inherited)
origin: workspace
---
```

### Pattern 3: Admin-Only API Routes

**What:** Separate router for workspace-level skill CRUD, protected to admin/owner only.
**When to use:** All endpoints under `/workspaces/{workspace_id}/workspace-role-skills`.

```python
# Source: modelled on role_skills.py router
router = APIRouter(
    prefix="/workspaces/{workspace_id}/workspace-role-skills",
    tags=["workspace-role-skills"]
)

# POST   /                        → generate + create (admin only, is_active=False)
# GET    /                        → list all workspace skills (admin sees all, member sees active)
# POST   /{skill_id}/activate     → approve (set is_active=True, admin only)
# PUT    /{skill_id}              → update content (admin only)
# DELETE /{skill_id}              → remove (admin only, soft delete)
```

Admin check pattern (matches Phase 13/14 pattern):
```python
async def _require_admin(
    workspace_id: UUID,
    current_user_id: CurrentUserId,
    session: SessionDep,
) -> None:
    from pilot_space.infrastructure.database.repositories.workspace_member_repository import (
        WorkspaceMemberRepository,
    )
    repo = WorkspaceMemberRepository(session)
    member = await repo.get_by_user_workspace(current_user_id, workspace_id)
    if member is None or member.role not in (WorkspaceRole.ADMIN, WorkspaceRole.OWNER):
        raise HTTPException(status_code=403, detail="Admin or owner required")
```

### Pattern 4: Frontend Admin Section

**What:** Admin-only section in the existing `SkillsSettingsPage` showing workspace-level skills. Non-admins do not see this section.
**When to use:** The page already has `workspaceStore.isAdmin` guard.

UI states for a workspace skill card:
- **Pending** (is_active=false): Yellow badge "Pending Review" + "Activate" button
- **Active** (is_active=true): Green badge "Active" + "Deactivate" button
- Both: Edit + Regenerate + Remove buttons (admin only)

### Anti-Patterns to Avoid

- **Reusing `UserRoleSkill` for workspace skills:** The unique constraint is on `(user_id, workspace_id, role_type)`. Workspace skills have no `user_id` (or a system user). Adding a nullable `user_id` to `UserRoleSkill` would require breaking the unique constraint and confuse the data model. Use a separate table.
- **Checking workspace role (OWNER/ADMIN/MEMBER) as the skill inheritance key:** The skill `role_type` is an SDLC concept (developer, tester, architect) not a workspace permission level. Inheritance is by matching `role_type` in the SDLC dimension, not `WorkspaceRole` in the permission dimension.
- **Materializing workspace skills globally (for all users):** Workspace skills are per-workspace, not global. Always filter by `workspace_id`.
- **Extending `pilotspace_agent.py`:** It's already at 698 lines. The materialization logic belongs in `role_skill_materializer.py`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| AI skill generation | Custom LLM pipeline | `GenerateRoleSkillService` (existing) | Already handles Claude Sonnet call, fallback, rate limiting, retries |
| Admin permission check | Custom role logic | `WorkspaceMemberRepository.get_by_user_workspace` + `WorkspaceRole` enum | Already implemented with correct enum casing |
| SKILL.md file injection | Custom file writing | Extend `materialize_role_skills()` | Already runs in every stream() call, handles cleanup |
| Workspace skill persistence | Custom SQL | SQLAlchemy + `WorkspaceScopedModel` base | RLS automatically applied via `WorkspaceScopedModel` |
| Rate limiting | Custom limiter | Existing `_check_rate_limit` in `generate_role_skill_service.py` | Already in-memory sliding window |
| Frontend data fetching | Custom fetch | TanStack Query + typed API client pattern | All hooks use this; use `useWorkspaceRoleSkills(workspaceId)` |

**Key insight:** The only net-new code is the `WorkspaceRoleSkill` model, its repository, the admin-only router, and extending the materializer. All logic (generation, approval-flag, file injection, admin checks) reuses existing patterns verbatim.

---

## Common Pitfalls

### Pitfall 1: UPPERCASE vs lowercase RLS enum
**What goes wrong:** RLS policies use `'OWNER'` and `'ADMIN'` (UPPERCASE) but queries that compare `WorkspaceRole.ADMIN.value` return `"ADMIN"` (UPPERCASE) — this is now consistent per migration 066 fix. The gotcha is `member.role` may be a string or enum depending on ORM load; use `.value` attribute consistently.
**Why it happens:** `WorkspaceRole` is a `str, Enum`; `.value` returns `"ADMIN"` (UPPERCASE). The in (`WorkspaceRole.ADMIN.value`, `WorkspaceRole.OWNER.value`) check is correct.
**How to avoid:** Compare `member.role in (WorkspaceRole.ADMIN, WorkspaceRole.OWNER)` when the column is an enum-typed SQLAlchemy `Mapped[WorkspaceRole]`.
**Warning signs:** `403` on admin endpoints even when logged in as admin.

### Pitfall 2: Materializer called without workspace skill loaded
**What goes wrong:** `materialize_role_skills` creates the skills sandbox directory per-session. If the workspace skill query runs on every stream() call (hot path), slow DB queries cause latency.
**Why it happens:** `set_rls_context()` must already be called before the workspace skill query (it's called before `materialize_role_skills` in the agent).
**How to avoid:** Filter query: `WHERE workspace_id = $1 AND is_active = true AND is_deleted = false` with index on `(workspace_id, is_active)`. This is O(workspace skills) which is expected to be small (at most N role types, ~9 possible).
**Warning signs:** p99 stream() latency increase.

### Pitfall 3: Unique constraint collision on generate+create
**What goes wrong:** Admin generates a skill for `developer` role, a workspace skill already exists (soft-deleted or inactive). The UNIQUE constraint on `(workspace_id, role_type)` raises `IntegrityError`.
**Why it happens:** `is_deleted=True` rows still participate in the UNIQUE constraint (PostgreSQL includes them unless filtered with a partial index).
**How to avoid:** Create the UNIQUE constraint as a partial index: `UNIQUE WHERE is_deleted = false`. Or: on generate, check for existing (including inactive) and offer "replace existing" flow. The simplest approach: `UPSERT` (INSERT ON CONFLICT UPDATE skill_content, is_active=False, updated_at=now()).
**Warning signs:** `409 Conflict` on second generate call for same role.

### Pitfall 4: dependencies.py and container.py already over 700 lines
**What goes wrong:** Adding new service deps to `dependencies.py` (712 lines) or container entries to `container.py` (743 lines) violates the 700-line file limit pre-commit check.
**Why it happens:** Both files are barrel/wiring files that grow with each phase.
**How to avoid:** Create a new `dependencies_workspace_skills.py` module for the workspace skill service deps. Register it in `wiring_config.modules` in `container.py` just for the new module path. Add minimal container entries (2-4 lines each), but do NOT add deps inline to `dependencies.py` — split to the new file.
**Warning signs:** Pre-commit `ruff check` file-length violation.

### Pitfall 5: Frontend `isAdmin` check matches settings module pattern
**What goes wrong:** Using `workspaceStore.currentUserRole === 'admin'` instead of `workspaceStore.isAdmin` (which also covers owner).
**Why it happens:** The `isAdmin` computed property returns true for both ADMIN and OWNER — this is already documented in `settings/README.md`.
**How to avoid:** Use `workspaceStore.isAdmin` consistently (see `SkillsSettingsPage` and `settings/README.md` permission table).

---

## Code Examples

Verified patterns from existing codebase:

### WorkspaceScopedModel base (for new model)
```python
# Source: backend/src/pilot_space/infrastructure/database/base.py
# WorkspaceScopedModel provides: id, workspace_id, created_at, updated_at,
# is_deleted, deleted_at; RLS via workspace_id FK.
class WorkspaceRoleSkill(WorkspaceScopedModel):
    __tablename__ = "workspace_role_skills"
    ...
```

### RLS migration pattern (migration 073)
```python
# Source: backend/alembic/versions/072_add_issue_suggestion_dismissals.py
op.execute(text("""
    ALTER TABLE workspace_role_skills ENABLE ROW LEVEL SECURITY;
    ALTER TABLE workspace_role_skills FORCE ROW LEVEL SECURITY;
    CREATE POLICY "workspace_isolation" ON workspace_role_skills
        FOR ALL TO authenticated
        USING (workspace_id::text = current_setting('app.current_workspace_id', true));
    CREATE POLICY "service_role_bypass" ON workspace_role_skills
        FOR ALL TO service_role USING (true);
"""))
```

### Service factory pattern (DI container)
```python
# Source: backend/src/pilot_space/container/container.py (lines 476-497)
# New workspace skill service follows same Factory pattern:
workspace_role_skill_service = providers.Factory(
    CreateWorkspaceRoleSkillService,
    session=session_factory,
)
```

### Admin permission guard pattern
```python
# Source: skill_approvals.py _verify_workspace_membership()
# Adapted for workspace skill admin check:
member = await repo.get_by_user_workspace(current_user_id, workspace_id)
if member is None or member.role not in (WorkspaceRole.ADMIN, WorkspaceRole.OWNER):
    raise HTTPException(status_code=403, detail="Admin or owner required")
```

### Materializer extension pattern
```python
# Source: backend/src/pilot_space/ai/agents/role_skill_materializer.py
# In materialize_role_skills(), AFTER writing user skills:
ws_repo = WorkspaceRoleSkillRepository(db_session)
workspace_skills = await ws_repo.get_active_by_workspace(workspace_id)
for ws_skill in workspace_skills:
    if ws_skill.role_type in user_role_types:
        continue  # WRSKL-04: user skill takes precedence
    dir_name = f"{_ROLE_SKILL_PREFIX}{ws_skill.role_type}"
    expected_dirs.add(dir_name)
    skill_dir = skills_dir / dir_name
    frontmatter = _build_workspace_frontmatter(ws_skill.role_name, ws_skill.role_type)
    content = f"{frontmatter}\n{ws_skill.skill_content}"
    await asyncio.to_thread(_write_skill_file, skill_dir, content)
```

### Frontend TanStack Query hook pattern
```typescript
// Source: frontend/src/features/settings/README.md + onboarding/hooks
// New hook follows useRoleSkills pattern:
export function useWorkspaceRoleSkills(workspaceId: string) {
  return useQuery({
    queryKey: ['workspace-role-skills', workspaceId],
    queryFn: () => workspaceRoleSkillsApi.getWorkspaceSkills(workspaceId),
    staleTime: 60_000,
    enabled: !!workspaceId,
  });
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Personal skills only (UserRoleSkill) | Add workspace-level skills (WorkspaceRoleSkill) | Phase 16 | Admins can standardize AI behavior across roles |
| materialize_role_skills loads user skills | Extend to load workspace skills as fallback | Phase 16 | WRSKL-03/04 — no change to agent interface |
| Admin views skills at /roles (personal only) | Admin section shows workspace skills with approval toggle | Phase 16 | New UI section, no route change needed |

**Not deprecated:**
- `UserRoleSkill` remains the primary personal skill store; `WorkspaceRoleSkill` is purely additive
- The `/role-skills` personal skill endpoints remain unchanged; new workspace skill endpoints are separate

---

## Open Questions

1. **Rate limiting for workspace skill generation**
   - What we know: `_check_rate_limit` gates by `user_id`, 5 generations/hour
   - What's unclear: Should workspace skill generation use the same per-user limit, or a separate per-workspace-admin limit?
   - Recommendation: Reuse the same `_check_rate_limit(user_id)` check (the admin's user_id). This is the simplest approach and matches existing behavior.

2. **Maximum workspace skills per workspace**
   - What we know: Personal skills cap at 3 per user-workspace. Workspace skills are per-workspace-role, so max is the number of valid role types (9: business_analyst, product_owner, developer, tester, architect, tech_lead, project_manager, devops, custom).
   - What's unclear: Should there be a lower cap?
   - Recommendation: No explicit cap — the UNIQUE constraint on `(workspace_id, role_type)` naturally limits to one per role type (at most 9).

3. **Workspace skill visibility to non-admin members**
   - What we know: WRSKL-03 says members inherit the skill; WRSKL-02 says it's inactive until admin approves.
   - What's unclear: Should non-admin members be able to LIST workspace skills (to know they exist)?
   - Recommendation: Admin-only read for inactive skills. Active skills are transparent (members just see the inherited skill in their AI context — no explicit "inherited" UI needed for members).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (backend), Vitest (frontend) |
| Config file | `backend/pyproject.toml`, `frontend/vitest.config.ts` |
| Quick run command | `cd backend && uv run pytest tests/unit/repositories/test_workspace_role_skill_repository.py -q` |
| Full suite command | `make quality-gates-backend` / `make quality-gates-frontend` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WRSKL-01 | Admin generates workspace skill content via AI | unit | `uv run pytest tests/unit/services/test_workspace_role_skill_service.py -x` | ❌ Wave 0 |
| WRSKL-02 | Skill inactive until admin activates; activate sets is_active=True | unit | `uv run pytest tests/unit/services/test_workspace_role_skill_service.py::test_activate -x` | ❌ Wave 0 |
| WRSKL-03 | Materializer injects workspace skill when no personal skill exists | unit | `uv run pytest tests/unit/ai/agents/test_role_skill_materializer.py::test_workspace_skill_inherited -x` | ❌ Wave 0 |
| WRSKL-04 | Personal skill takes precedence over workspace skill | unit | `uv run pytest tests/unit/ai/agents/test_role_skill_materializer.py::test_personal_skill_overrides_workspace -x` | ❌ Wave 0 |
| WRSKL-01 | Admin-only POST endpoint returns 403 for non-admin | unit | `uv run pytest tests/unit/api/test_workspace_role_skills_router.py::test_create_forbidden_for_member -x` | ❌ Wave 0 |
| WRSKL-02 | Activate endpoint returns 403 for non-admin | unit | `uv run pytest tests/unit/api/test_workspace_role_skills_router.py::test_activate_forbidden -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/repositories/test_workspace_role_skill_repository.py tests/unit/services/test_workspace_role_skill_service.py tests/unit/ai/agents/test_role_skill_materializer.py -q`
- **Per wave merge:** `make quality-gates-backend`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/repositories/test_workspace_role_skill_repository.py` — covers model CRUD + UNIQUE constraint
- [ ] `tests/unit/services/test_workspace_role_skill_service.py` — covers generate, activate, list, delete (WRSKL-01, WRSKL-02)
- [ ] `tests/unit/api/test_workspace_role_skills_router.py` — covers admin-only guards + 403 paths (WRSKL-01, WRSKL-02)
- [ ] Extend `tests/unit/ai/agents/test_role_skill_materializer.py` — covers workspace skill injection and personal-override behavior (WRSKL-03, WRSKL-04)
- [ ] `frontend/src/features/settings/components/__tests__/workspace-skill-card.test.tsx` — Wave 0 vitest stubs
- [ ] `frontend/src/services/api/__tests__/workspace-role-skills.test.ts` — Wave 0 API client stubs

---

## Sources

### Primary (HIGH confidence)
- `backend/src/pilot_space/infrastructure/database/models/user_role_skill.py` — `UserRoleSkill` model reference implementation
- `backend/src/pilot_space/ai/agents/role_skill_materializer.py` — materialization injection point (verified)
- `backend/src/pilot_space/application/services/role_skill/` — generation service with AI + fallback (verified)
- `backend/src/pilot_space/api/v1/routers/role_skills.py` — router pattern reference (verified)
- `backend/src/pilot_space/infrastructure/database/models/workspace_member.py` — `WorkspaceRole` enum values (verified)
- `backend/src/pilot_space/api/v1/routers/skill_approvals.py` — admin-check pattern reference (verified)
- `frontend/src/features/settings/pages/skills-settings-page.tsx` — skills page structure + `isAdmin` guard (verified)
- `frontend/src/services/api/role-skills.ts` — API client pattern reference (verified)

### Secondary (MEDIUM confidence)
- `backend/alembic/versions/072_add_issue_suggestion_dismissals.py` — confirms migration head is 072, next is 073
- `.planning/STATE.md` Decisions log — confirms dependencies.py at 712 lines, container.py at 743 lines (need new deps file)

### Tertiary (LOW confidence)
- None — all claims verified from source

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — uses existing libraries, no new dependencies
- Architecture: HIGH — directly extends documented existing patterns
- Pitfalls: HIGH — identified from actual file sizes, enum casing fix (migration 066), and existing unique constraint patterns

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable codebase, no fast-moving external deps)

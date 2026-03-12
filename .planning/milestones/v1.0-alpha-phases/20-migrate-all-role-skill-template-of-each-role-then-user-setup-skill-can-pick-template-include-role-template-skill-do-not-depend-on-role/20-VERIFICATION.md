---
phase: 20-skill-template-catalog
verified: 2026-03-11T14:30:00Z
status: gaps_found
score: 5/6 must-haves verified
gaps:
  - truth: "Admin can create/manage workspace templates; built-in templates are read-only"
    status: partial
    reason: "Frontend edit action for workspace templates shows 'coming soon' toast instead of actual edit modal. Backend PATCH endpoint exists and works, but frontend has no edit UI."
    artifacts:
      - path: "frontend/src/features/settings/pages/skills-settings-page.tsx"
        issue: "handleEditTemplate (line 148-151) is a stub: toast.info('coming soon') instead of opening edit modal"
    missing:
      - "Edit template modal component that calls useUpdateSkillTemplate mutation for workspace templates (name, description, skill_content, icon fields)"
---

# Phase 20: Skill Template Catalog Verification Report

**Phase Goal:** Decouple skills from roles -- create skill_templates table, user_skills table, migrate existing role_skills data, and build a frontend template catalog where users browse and personalize skill templates independently of their workspace role.
**Verified:** 2026-03-11T14:30:00Z
**Status:** gaps_found
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | skill_templates and user_skills tables exist with data migrated from legacy tables (old tables NOT dropped) | VERIFIED | Migration 077 creates both tables with RLS. INSERT INTO statements copy from role_templates, workspace_role_skills, user_role_skills. No DROP TABLE in upgrade. |
| 2 | Materializer reads from new tables with OperationalError fallback to legacy | VERIFIED | `_materialize_from_new_tables()` reads UserSkillRepository + SkillTemplateRepository. `materialize_role_skills()` wraps in try/except OperationalError fallback to `_materialize_from_legacy_tables()`. |
| 3 | Built-in templates seeded per workspace at creation time | VERIFIED | `SeedTemplatesService.seed_workspace()` copies RoleTemplate rows into skill_templates (source='built_in'). Idempotent guard checks for existing built_in rows. Non-fatal try/except. |
| 4 | Admin can create/manage workspace templates; built-in templates are read-only | PARTIAL | Backend: full CRUD works (POST create, PATCH update with built-in guard, DELETE soft-delete). Frontend: Create Template modal works, delete works, deactivate toggle works, BUT edit workspace template shows "coming soon" toast stub (line 150). |
| 5 | Users browse template catalog, pick a template, and AI generates personalized skill | VERIFIED | TemplateCatalog renders template cards with "Use This" button. handleUseThis opens SkillGeneratorModal with template prop. POST /user-skills delegates to CreateUserSkillService which calls GenerateRoleSkillService for AI content. |
| 6 | Skills settings page shows My Skills + Template Catalog sections | VERIFIED | SkillsSettingsPage renders "My Skills" section (MySkillCard grid) + "Skill Templates" section (TemplateCatalog). useUserSkills hook for personal skills, useSkillTemplates for catalog. Empty state prompts browsing templates. |

**Score:** 5/6 truths verified (1 partial)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/.../models/skill_template.py` | SkillTemplate model | VERIFIED | WorkspaceScopedModel, source enum, nullable role_type, is_active defaults true, check constraints, partial unique index |
| `backend/.../models/user_skill.py` | UserSkill model | VERIFIED | user_id FK CASCADE, template_id FK SET NULL nullable, no role_type, joined relationships |
| `backend/.../models/__init__.py` | Model registration | VERIFIED | Both SkillTemplate and UserSkill imported and exported |
| `backend/alembic/versions/077_*.py` | Migration with data migration + RLS | VERIFIED | Schema creation + 3 INSERT INTO statements + RLS ENABLE/FORCE + no old table drops |
| `backend/.../repositories/skill_template_repository.py` | CRUD repository | VERIFIED | get_active_by_workspace, get_by_workspace, create, update, soft_delete |
| `backend/.../repositories/user_skill_repository.py` | CRUD repository | VERIFIED | get_by_user_workspace, get_by_user_workspace_template, create, update, soft_delete |
| `backend/.../ai/agents/role_skill_materializer.py` | Refactored materializer | VERIFIED | New + legacy paths, _sanitize_skill_dir_name, 530 lines (under 700) |
| `backend/.../services/skill_template/seed_templates_service.py` | Workspace seeding | VERIFIED | Idempotent, non-fatal, copies RoleTemplate rows |
| `backend/.../services/user_skill/create_user_skill_service.py` | AI personalization | VERIFIED | Template validation, duplicate check, AI generation via GenerateRoleSkillService |
| `backend/.../routers/skill_templates.py` | Admin CRUD router | VERIFIED | GET (all), POST/PATCH/DELETE (admin), built-in read-only guard |
| `backend/.../routers/user_skills.py` | User skills router | VERIFIED | GET/POST/PATCH/DELETE with ownership guard, POST delegates to CreateUserSkillService |
| `backend/.../schemas/skill_template.py` | Pydantic schemas | VERIFIED | SkillTemplateSchema, Create, Update with ConfigDict(from_attributes=True) |
| `backend/.../schemas/user_skill.py` | Pydantic schemas | VERIFIED | UserSkillSchema with template_name, Create, Update |
| `frontend/src/services/api/skill-templates.ts` | TanStack Query hooks | VERIFIED | 4 hooks, typed interfaces, query key invalidation |
| `frontend/src/services/api/user-skills.ts` | TanStack Query hooks | VERIFIED | 4 hooks, typed interfaces, query key invalidation |
| `frontend/.../settings/pages/skills-settings-page.tsx` | Restructured page | VERIFIED | My Skills + Template Catalog sections, admin Create Template button |
| `frontend/.../settings/components/template-catalog.tsx` | Observer catalog grid | VERIFIED | useSkillTemplates, role-type filter chips, loading skeletons, TemplateCard rendering |
| `frontend/.../settings/components/template-card.tsx` | Template card | VERIFIED | Source badges (blue/green/purple), lock icon for built-in, admin dropdown, "Use This" button |
| `frontend/.../settings/components/my-skill-card.tsx` | User skill card | VERIFIED | Status dot, toggle active, delete, template_name display |
| `frontend/.../settings/components/create-template-modal.tsx` | Admin create modal | VERIFIED | Form with name/description/content/icon, useCreateSkillTemplate mutation |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| Migration 077 | skill_templates table | op.create_table + INSERT INTO | WIRED | 3 data migration INSERT statements present |
| SkillTemplate model | WorkspaceScopedModel | class inheritance | WIRED | `class SkillTemplate(WorkspaceScopedModel)` |
| role_skill_materializer.py | UserSkillRepository | import and query | WIRED | Lazy import inside `_materialize_from_new_tables`, instantiated and queried |
| role_skill_materializer.py | SkillTemplateRepository | import and fallback query | WIRED | Lazy import, used for active templates not covered by user skills |
| seed_templates_service.py | RoleTemplateRepository | reads built-in templates | WIRED | `role_repo.get_all_ordered()` called, results iterated and copied |
| skill_templates router | SkillTemplateRepository | direct instantiation | WIRED | `SkillTemplateRepository(session)` in every endpoint |
| user_skills router | CreateUserSkillService | direct instantiation for POST | WIRED | `CreateUserSkillService(session)` in create_user_skill endpoint |
| routers/__init__.py | skill_templates.router | import and export | WIRED | `from ... import router as skill_templates_router` + in __all__ |
| main.py | both routers | include_router | WIRED | `app.include_router(skill_templates_router, prefix=...)` and user_skills_router |
| skill-templates.ts | /workspaces/{slug}/skill-templates | apiClient | WIRED | apiClient.get/post/patch/delete with correct paths |
| user-skills.ts | /workspaces/{slug}/user-skills | apiClient | WIRED | apiClient.get/post/patch/delete with correct paths |
| skills-settings-page.tsx | template-catalog.tsx | component composition | WIRED | `<TemplateCatalog workspaceSlug={...} isAdmin={...} onUseThis={...} />` |
| skills-settings-page.tsx | SkillGeneratorModal | template prop | WIRED | `template={selectedTemplate}` passed, modal accepts optional template prop |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| P20-01 | 20-01 | skill_templates table | SATISFIED | Model + migration with correct schema |
| P20-02 | 20-01 | user_skills table | SATISFIED | Model + migration with correct schema |
| P20-03 | 20-01 | Data migration from legacy tables | SATISFIED | Migration 077 INSERT INTO statements |
| P20-04 | 20-02 | Materializer reads new tables | SATISFIED | _materialize_from_new_tables with fallback |
| P20-05 | 20-03 | Skill templates admin CRUD API | SATISFIED | Router with GET/POST/PATCH/DELETE, admin guard |
| P20-06 | 20-03 | User skills CRUD API | SATISFIED | Router with owner-only CRUD, AI personalization |
| P20-07 | 20-02 | Built-in template seeding | SATISFIED | SeedTemplatesService with idempotency |
| P20-08 | 20-02 | AI personalization from template | SATISFIED | CreateUserSkillService with GenerateRoleSkillService |
| P20-09 | 20-04 | Frontend template catalog UI | SATISFIED | TemplateCatalog, TemplateCard, filter chips |
| P20-10 | 20-04 | Frontend my skills management | SATISFIED | MySkillCard, toggle/delete actions |

Note: P20-01 through P20-10 are referenced in ROADMAP.md and plan frontmatters but not defined in REQUIREMENTS.md. No orphaned requirements found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/.../skills-settings-page.tsx` | 150 | `toast.info("coming soon")` in handleEditTemplate | Warning | Admin cannot edit workspace template fields from UI. Backend PATCH works, frontend has no edit modal. |

### Human Verification Required

### 1. Template Catalog Visual Layout

**Test:** Navigate to `http://localhost:3000/{workspace}/skills` and verify the Skills tab shows "My Skills" section followed by "Skill Templates" grid.
**Expected:** Responsive grid (1/2/3 cols), template cards with icon hero area, source badges (blue=built-in, green=workspace), filter chips for role types.
**Why human:** Visual layout, responsive behavior, and design quality cannot be verified programmatically.

### 2. "Use This" AI Personalization Flow

**Test:** Click "Use This" on a template card. Verify SkillGeneratorModal opens with template content pre-filled.
**Expected:** Modal shows template name/description, user can enter experience, AI generates personalized skill, skill appears in "My Skills" section.
**Why human:** End-to-end flow involving AI generation, modal interaction, and real-time UI update.

### 3. Admin Template Management

**Test:** As admin, verify "Create Template" button visible, opens modal, can create workspace template. Verify built-in templates show lock icon with only deactivate toggle (no edit/delete).
**Expected:** New workspace template appears in catalog. Built-in templates restricted to deactivate only.
**Why human:** Role-based UI visibility and interaction behavior.

### 4. Plugins and Action Buttons Tabs Unchanged

**Test:** Switch to Plugins and Action Buttons tabs. Verify they still render correctly.
**Expected:** Both tabs function as before Phase 20 changes.
**Why human:** Regression verification of existing UI.

### Gaps Summary

One gap identified: the frontend edit action for workspace templates is a stub that shows a "coming soon" toast instead of opening an edit modal. The backend PATCH endpoint is fully functional with proper built-in guard logic, and the `useUpdateSkillTemplate` mutation hook exists in the frontend. The missing piece is a UI modal that allows admins to edit workspace template fields (name, description, skill_content, icon). This is the only incomplete aspect of the "Admin can create/manage workspace templates" success criterion.

All other success criteria are fully verified:
- Database tables with data migration and RLS
- Materializer refactored with fallback
- Template seeding service
- Full API layer (routers + schemas)
- Frontend catalog with template cards, source badges, filter chips
- My Skills section with toggle and delete
- "Use This" to AI personalization flow

---

_Verified: 2026-03-11T14:30:00Z_
_Verifier: Claude (gsd-verifier)_

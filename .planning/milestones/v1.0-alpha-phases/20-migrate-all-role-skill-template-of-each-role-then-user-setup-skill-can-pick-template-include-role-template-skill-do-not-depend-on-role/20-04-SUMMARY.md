---
phase: 20-skill-template-catalog
plan: 04
subsystem: ui
tags: [react, tanstack-query, shadcn-ui, skill-templates, user-skills, template-catalog]

# Dependency graph
requires:
  - phase: 20-skill-template-catalog-03
    provides: Skill templates CRUD router and user skills CRUD router with Pydantic schemas
provides:
  - TanStack Query hooks for skill templates and user skills APIs
  - Template catalog browsable UI with source badges and role-type filter chips
  - My Skills section with compact horizontal cards
  - Create Template modal for workspace admins
  - Restructured Skills settings page (My Skills + Template Catalog)
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [template-catalog-grid, role-type-filter-chips, source-badge-color-coding, template-to-generator-flow]

key-files:
  created:
    - frontend/src/services/api/skill-templates.ts
    - frontend/src/services/api/user-skills.ts
    - frontend/src/services/api/user-skills.test.ts
    - frontend/src/features/settings/components/template-card.tsx
    - frontend/src/features/settings/components/my-skill-card.tsx
    - frontend/src/features/settings/components/template-catalog.tsx
    - frontend/src/features/settings/components/create-template-modal.tsx
  modified:
    - frontend/src/features/settings/pages/skills-settings-page.tsx
    - frontend/src/features/settings/pages/__tests__/skills-settings-page.test.tsx
    - frontend/src/features/settings/components/skill-generator-modal.tsx

key-decisions:
  - "TemplateCatalog is observer, TemplateCard and MySkillCard are plain components -- observer for data fetching, plain for props-driven leaf components"
  - "Removed MAX_SKILLS=3 cap -- users can have multiple active skills per Phase 20 design"
  - "Source badge color coding: blue=built-in, green=workspace, purple=custom -- visually distinguishes template origins"
  - "Built-in templates show lock icon + only deactivate in admin dropdown (no edit/delete) -- preserves platform content"
  - "SkillGeneratorModal receives template prop to pre-fill header and description from 'Use This' flow"
  - "Role-type filter chips in TemplateCatalog for browsing by category"

patterns-established:
  - "Template catalog grid: responsive 3-col (lg) / 2-col (md) / 1-col (sm) with source badges"
  - "Template-to-generator flow: 'Use This' passes SkillTemplate to SkillGeneratorModal for AI personalization"
  - "Admin vs member UI gating: Create Template button and template dropdown actions conditional on isAdmin"

requirements-completed: [P20-09, P20-10]

# Metrics
duration: 10min
completed: 2026-03-11
---

# Phase 20 Plan 04: Frontend Template Catalog UI Summary

**Skill template catalog with browsable cards, role-type filter chips, My Skills management section, and restructured settings page using TanStack Query hooks**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-11T13:59:20Z
- **Completed:** 2026-03-11T14:09:20Z
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments
- TanStack Query hooks for both skill templates and user skills APIs (8 hooks total with typed interfaces and cache invalidation)
- Template catalog UI with responsive grid, source badges (built-in/workspace/custom), role-type filter chips, and "Use This" flow
- My Skills section with compact horizontal skill cards, active/inactive status, toggle and delete actions
- Skills settings page restructured: My Skills at top, Skill Templates below, Create Template for admins, no skill cap
- Design polish: large icon hero area on template cards, hover effects, loading skeletons matching card shapes
- 16 tests passing (6 API hook tests + 10 page tests covering all states)

## Task Commits

Each task was committed atomically:

1. **Task 1: API hooks for skill templates and user skills** - `a101f1ed` (feat, TDD)
2. **Task 2: Template catalog components + restructured Skills settings page** - `8cb16870` (feat)
3. **Task 3: Visual verification + design enhancements** - `020d0781` (feat)

## Files Created/Modified
- `frontend/src/services/api/skill-templates.ts` - SkillTemplate types + useSkillTemplates, useCreateSkillTemplate, useUpdateSkillTemplate, useDeleteSkillTemplate hooks
- `frontend/src/services/api/user-skills.ts` - UserSkill types + useUserSkills, useCreateUserSkill, useUpdateUserSkill, useDeleteUserSkill hooks
- `frontend/src/services/api/user-skills.test.ts` - 6 tests for API hooks (query keys, mutations, cache invalidation)
- `frontend/src/features/settings/components/template-card.tsx` - Template card with icon hero, source badge, admin dropdown, "Use This" button
- `frontend/src/features/settings/components/my-skill-card.tsx` - Compact horizontal user skill card with status dot
- `frontend/src/features/settings/components/template-catalog.tsx` - Observer grid with role-type filter chips, loading skeletons, error/empty states
- `frontend/src/features/settings/components/create-template-modal.tsx` - Admin dialog for creating workspace templates
- `frontend/src/features/settings/pages/skills-settings-page.tsx` - Restructured with My Skills + Template Catalog sections
- `frontend/src/features/settings/pages/__tests__/skills-settings-page.test.tsx` - 10 tests for restructured page
- `frontend/src/features/settings/components/skill-generator-modal.tsx` - Added template prop for "Use This" pre-fill

## Decisions Made
- TemplateCatalog is observer (fetches data), TemplateCard and MySkillCard are plain components (receive props) -- follows existing PluginsTabContent/PluginCard pattern
- Removed MAX_SKILLS=3 cap -- Phase 20 decouples skills from roles, users can have multiple active skills
- Source badge color coding (blue/green/purple) -- consistent with existing badge patterns in plugin-card
- Built-in templates read-only in admin UI (lock icon, only deactivate toggle) -- matches backend guard from Plan 03
- SkillGeneratorModal receives optional template prop -- "Use This" passes template to pre-fill the generation flow
- Role-type filter chips in catalog -- enables browsing templates by category (e.g., developer, tester, architect)
- Page uses useUserSkills (new) instead of useRoleSkills (legacy) -- new data model from Phase 20

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Rewrote skills-settings-page tests for new data model**
- **Found during:** Task 2
- **Issue:** Existing tests used useRoleSkills and old page structure (MAX_SKILLS, SkillCard with isPrimary). Page now uses useUserSkills with MySkillCard.
- **Fix:** Rewrote test file with new mocks, QueryClientProvider wrapper, and assertions matching the restructured page
- **Files modified:** frontend/src/features/settings/pages/__tests__/skills-settings-page.test.tsx
- **Verification:** All 10 tests pass
- **Committed in:** 8cb16870 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Test rewrite necessary because page structure changed. No scope creep.

## Issues Encountered
- Pre-existing test failures in audit-settings-page.test.tsx (missing useRollbackAIArtifact mock) and api-key-form.test.tsx (missing validationErrors property) -- unrelated to this plan, not addressed.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 20 complete: all 4 plans executed
- Skill templates browseable, user skills manageable, template catalog UI live
- End-to-end flow: browse templates -> "Use This" -> AI personalization -> My Skills

---
*Phase: 20-skill-template-catalog*
*Completed: 2026-03-11*

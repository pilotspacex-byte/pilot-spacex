---
phase: 019-skill-registry-and-plugin-system
plan: 04
subsystem: ui
tags: [react, mobx, shadcn, tabs, sheet, plugin-marketplace, tanstack-query]

requires:
  - phase: 019-01
    provides: xfail test stubs for PluginsStore and PluginCard
  - phase: 019-03
    provides: backend REST API endpoints for plugins CRUD, browse, check-updates, github-credential

provides:
  - pluginsApi typed API client for all plugin endpoints
  - PluginsStore MobX observable store with full plugin lifecycle
  - PluginCard component with status badges (Installed, Update Available orange chip)
  - PluginDetailSheet 3-tab slide-over (Overview, SKILL.md, References)
  - AddRepoForm for browsing GitHub repos
  - GitHubAccessSection for PAT management
  - PluginsTabContent observer wrapper for isolated reactivity
  - SkillsSettingsPage extended with Roles/Plugins tab navigation

affects: [017-skill-action-buttons, frontend-settings]

tech-stack:
  added: []
  patterns: [observer-child-component for tab isolation, props-based PluginCard without observer]

key-files:
  created:
    - frontend/src/services/api/plugins.ts
    - frontend/src/stores/ai/PluginsStore.ts
    - frontend/src/features/settings/components/plugin-card.tsx
    - frontend/src/features/settings/components/plugin-detail-sheet.tsx
    - frontend/src/features/settings/components/add-repo-form.tsx
    - frontend/src/features/settings/components/github-access-section.tsx
    - frontend/src/features/settings/components/plugins-tab-content.tsx
  modified:
    - frontend/src/stores/ai/AIStore.ts
    - frontend/src/stores/ai/index.ts
    - frontend/src/features/settings/pages/skills-settings-page.tsx
    - frontend/src/stores/ai/__tests__/PluginsStore.test.ts
    - frontend/src/features/settings/components/__tests__/plugin-card.test.tsx

key-decisions:
  - "PluginsTabContent as separate observer() component to keep SkillsSettingsPage under 700 lines and isolate MobX reactivity"
  - "PluginCard uses props (not observer) — parent passes values, card stays pure for testability"
  - "Plugins tab visible only to admin users (workspaceStore.isAdmin check)"
  - "SKILL.md and References tabs show placeholder — API does not expose content yet"

patterns-established:
  - "Observer child component pattern: large existing page + new reactive section = extract child as observer()"
  - "PluginCard status badge: has_update → orange chip, installed → green Badge variant=secondary"

requirements-completed: [SKRG-01, SKRG-02, SKRG-03, SKRG-04, SKRG-05]

duration: 9min
completed: 2026-03-10
---

# Phase 19 Plan 04: Plugin Marketplace UI Summary

**Plugin marketplace UI with browse, install, update badges, detail sheet, GitHub PAT management, all within Settings Skills Plugins tab**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-10T15:28:47Z
- **Completed:** 2026-03-10T15:37:49Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments
- Complete plugin API client with typed endpoints for CRUD, browse, check-updates, and GitHub credential
- MobX PluginsStore with full lifecycle: load, fetchRepo, install, uninstall, checkUpdates, saveGitHubPat
- Plugin card component showing orange "Update Available" chip and green "Installed" badge
- Plugin detail sheet with 3 tabs (Overview, SKILL.md, References)
- GitHub PAT management section with status indicator
- Skills settings page extended with Roles/Plugins tab navigation (admin only)
- 20 unit tests (13 PluginsStore + 7 PluginCard) all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: API client + PluginsStore + AIStore wiring** - `621c28fb` (feat, TDD)
2. **Task 2: Plugin UI components + Settings page extension** - `cab3f7bd` (feat)

## Files Created/Modified
- `frontend/src/services/api/plugins.ts` - Typed API client for all plugin endpoints
- `frontend/src/stores/ai/PluginsStore.ts` - MobX store with full plugin lifecycle management
- `frontend/src/stores/ai/AIStore.ts` - Added plugins: PluginsStore alongside mcpServers
- `frontend/src/stores/ai/index.ts` - Barrel exports for PluginsStore and types
- `frontend/src/features/settings/components/plugin-card.tsx` - Card with status badges and install/update actions
- `frontend/src/features/settings/components/plugin-detail-sheet.tsx` - 3-tab slide-over sheet
- `frontend/src/features/settings/components/add-repo-form.tsx` - GitHub repo URL browse form
- `frontend/src/features/settings/components/github-access-section.tsx` - PAT input with status
- `frontend/src/features/settings/components/plugins-tab-content.tsx` - Observer wrapper for Plugins tab
- `frontend/src/features/settings/pages/skills-settings-page.tsx` - Extended with Roles/Plugins tabs
- `frontend/src/stores/ai/__tests__/PluginsStore.test.ts` - 13 unit tests
- `frontend/src/features/settings/components/__tests__/plugin-card.test.tsx` - 7 unit tests

## Decisions Made
- PluginsTabContent extracted as separate observer() to keep SkillsSettingsPage under 700 lines and isolate MobX plugin reactivity from the existing role skills observer tree
- PluginCard uses plain props (not observer) for testability and simplicity
- Plugins tab conditionally rendered for admin users only (workspaceStore.isAdmin)
- SKILL.md and References tabs in detail sheet show placeholder text since the API does not expose raw content yet

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused React imports in non-observer components**
- **Found during:** Task 2
- **Issue:** TypeScript error TS6133 — React imported but not used in plugin-card.tsx and plugin-detail-sheet.tsx (Next.js JSX transform doesn't need it)
- **Fix:** Removed `import * as React from 'react'` from both files
- **Verification:** `pnpm type-check` reports 0 errors
- **Committed in:** cab3f7bd (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Trivial fix for unused import. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plugin marketplace UI complete and ready for manual verification
- Phase 19 (Skill Registry and Plugin System) is now fully complete (all 4 plans)
- Next: Phase 17 (Skill Action Buttons) can wire MCP/action button UI to installed plugins

---
*Phase: 019-skill-registry-and-plugin-system*
*Completed: 2026-03-10*

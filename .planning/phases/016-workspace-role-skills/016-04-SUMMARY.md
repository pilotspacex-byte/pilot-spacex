---
phase: "016-workspace-role-skills"
plan: "04"
subsystem: "frontend/settings"
status: "complete"
tags: ["frontend", "settings", "workspace-skills", "admin-ui", "tanstack-query"]
dependency_graph:
  requires:
    - "016-03"  # backend router + materializer
  provides:
    - "workspace-role-skills-api-client"
    - "WorkspaceSkillCard"
    - "SkillsSettingsPage-admin-section"
  affects:
    - "frontend/src/features/settings/pages/skills-settings-page.tsx"
tech_stack:
  added: []
  patterns:
    - "TanStack Query useQuery + useMutation for workspace-role-skills"
    - "WorkspaceSkillCard with is_active one-way gate (no Deactivate)"
    - "workspaceStore.isAdmin conditional render for admin section"
key_files:
  created:
    - "frontend/src/services/api/workspace-role-skills.ts"
    - "frontend/src/features/settings/components/workspace-skill-card.tsx"
  modified:
    - "frontend/src/features/settings/pages/skills-settings-page.tsx"
    - "frontend/src/features/settings/components/__tests__/workspace-skill-card.test.tsx"
decisions:
  - "No Deactivate button on WorkspaceSkillCard: is_active is a one-way approval gate; to revert, remove and regenerate"
  - "useWorkspaceRoleSkills enabled only when workspaceId truthy and workspaceStore.isAdmin"
  - "Generate dialog uses inline form (no separate component) — stays under 700-line limit"
metrics:
  duration_minutes: 14
  completed_date: "2026-03-10"
  tasks_completed: 2
  tasks_total: 3
  files_changed: 4
---

# Phase 16 Plan 04: Workspace Role Skills Admin UI Summary

**One-liner:** TypeScript API client + WorkspaceSkillCard with one-way activation gate + admin section in SkillsSettingsPage wired to TanStack Query.

## Status: COMPLETE

All tasks done. Human verification passed 2026-03-10. Additional bug fixed during verification.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Typed API client + TanStack Query hooks | `0da97e11` | `workspace-role-skills.ts` (created) |
| 2 | WorkspaceSkillCard + admin section in SkillsSettingsPage | `a0ce03c6` | `workspace-skill-card.tsx` (created), `skills-settings-page.tsx` (modified), `workspace-skill-card.test.tsx` (7 tests) |

## What Was Built

### Task 1: `frontend/src/services/api/workspace-role-skills.ts`
- `workspaceRoleSkillsApi`: 4 methods (get, generate, activate, delete)
- `useWorkspaceRoleSkills(workspaceId)` — query, enabled only when workspaceId truthy
- `useGenerateWorkspaceSkill`, `useActivateWorkspaceSkill`, `useDeleteWorkspaceSkill` — mutations that invalidate `['workspace-role-skills', workspaceId]` on success
- Exported types: `WorkspaceRoleSkill`, `WorkspaceRoleSkillsResponse`, `GenerateWorkspaceSkillPayload`
- No deactivate mutation — documented in JSDoc

### Task 2: `frontend/src/features/settings/components/workspace-skill-card.tsx`
- Pending state (isActive=false): yellow "Pending Review" badge + "Activate" + "Remove" buttons
- Active state (isActive=true): green "Active" badge + "Remove" button only
- No Deactivate button — enforces one-way gate semantics

### Task 2: Admin section in `skills-settings-page.tsx`
- Visible only when `workspaceStore.isAdmin` is true
- "Generate Skill" dialog with roleType Select, roleName Input, experienceDescription Textarea
- WorkspaceSkillCard list with activate/remove handlers
- Remove confirmation using `ConfirmActionDialog`
- File: 587 lines (under 700-line limit)

## Quality Gates

- `pnpm type-check`: PASSED (0 errors)
- `pnpm lint`: PASSED (0 errors, 22 pre-existing warnings in other files)
- `pnpm test --run` (workspace-skill-card suite): 7/7 PASSED
- Pre-existing failures in other test suites (207 failures) not caused by this plan

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused `import * as React from 'react'` in WorkspaceSkillCard**
- **Found during:** Type-check after Task 2
- **Issue:** `error TS6133: 'React' is declared but its value is never read` — Next.js/React 17+ doesn't need explicit React import for JSX
- **Fix:** Removed unused import
- **Files modified:** `workspace-skill-card.tsx`
- **Commit:** included in `a0ce03c6`

## Human Verification Results (2026-03-10)

| Step | Test | Result |
|------|------|--------|
| 7 | Pending Review badge + Activate + Remove (no Deactivate) | ✅ |
| 8 | Activate → green Active badge, only Remove remains | ✅ |
| 9 | Remove → confirmation dialog → skill disappears | ✅ |
| 10 | MEMBER user: Skill section NOT visible | ✅ |

### Bug Fixed During Verification

**FastAPI trailing slash redirect leaks backend URL through Next.js proxy**

- Route decorators used `"/"` → FastAPI issued 307 redirects with absolute `http://localhost:8000/...` Location header
- Next.js proxy forwarded 307 directly to browser; browser dropped `Authorization` header on cross-origin follow
- Result: 401 from backend, TanStack Query cache stuck at `null`
- Fix: Changed `@router.get("/")` and `@router.post("/")` to `""` in `workspace_role_skills.py`
- Commit: `1d17afa9`

Also fixed during development (prior commits):
- Snake_case field names in `WorkspaceRoleSkill` interface (was camelCase)
- Section heading renamed "Workspace Role Skills" → "Skill"

## Self-Check

- [x] `frontend/src/services/api/workspace-role-skills.ts` — FOUND
- [x] `frontend/src/features/settings/components/workspace-skill-card.tsx` — FOUND
- [x] `frontend/src/features/settings/pages/skills-settings-page.tsx` — FOUND (modified)
- [x] Commit `0da97e11` — FOUND
- [x] Commit `a0ce03c6` — FOUND

## Self-Check: PASSED

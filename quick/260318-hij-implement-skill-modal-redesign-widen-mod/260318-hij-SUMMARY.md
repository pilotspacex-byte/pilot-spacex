---
phase: quick-260318-hij
plan: 01
subsystem: frontend/settings
tags: [ui, modal, skill-creation, dual-mode, tabs]
dependency_graph:
  requires: [user-skills-api, onboarding-hooks, workspace-role-skills-api]
  provides: [SkillAddModal, dual-mode-skill-creation]
  affects: [skills-settings-page]
tech_stack:
  added: []
  patterns: [shadcn-tabs, dual-mode-modal, TDD-red-green]
key_files:
  created:
    - frontend/src/features/settings/components/skill-add-modal.tsx
    - frontend/src/features/settings/components/__tests__/skill-add-modal.test.tsx
  modified:
    - frontend/src/features/settings/pages/skills-settings-page.tsx
    - frontend/src/features/settings/components/skill-generator-modal.tsx
    - frontend/src/features/settings/components/index.ts
decisions:
  - "Inline toolbar from SkillEditor instead of importing it (SkillEditor has built-in Save/Cancel that conflict with shared footer)"
  - "Use deferred promise in test 7 to observe transient generating state"
  - "ModeToggle uses render-function pattern to reduce duplication"
metrics:
  duration_seconds: 584
  completed: "2026-03-18T05:50:45Z"
  tasks_completed: 2
  tasks_total: 2
  test_count: 12
  files_created: 2
  files_modified: 3
---

# Quick Task 260318-hij: Skill Modal Redesign Summary

Dual-mode Add Skill modal with Manual tab (direct name + content input) and AI Generate tab (preserved existing flow), widened to 896px single-column layout.

## What Was Done

### Task 1: Create SkillAddModal with Manual + AI Generate tabs (TDD)

**Commit:** 1558e4b7

Created `skill-add-modal.tsx` (682 lines after prettier) implementing the full UX spec:

- **Modal shell**: `sm:max-w-4xl` (896px), `max-h-[85vh]`, flex column layout, `p-0` on DialogContent
- **Header**: "Add Skill" title + ModeToggle (personal/workspace) when `showModeToggle` is true
- **Tabs**: shadcn Tabs with "Manual" and "AI Generate" triggers, disabled during generation
- **Manual tab**: name input (required, blur validation), description input (optional, maps to experience_description), markdown toolbar + textarea (min-h-[320px]), WordCountBar, inline tip
- **AI Generate tab**: form step (description textarea min-h-[260px]), generating step (progress animation), preview step (editable name + content, WordCountBar, "Back to description" button)
- **Footer**: button matrix per spec -- Manual: Cancel + Save Skill; AI form: Cancel + Generate; AI generating: hidden; AI preview: Retry + Save & Activate
- **State management**: all React useState, no MobX. Tab switching preserves state both directions.
- **Template pre-seed**: when template prop provided, AI tab active, description pre-filled

**Tests**: 12 tests covering all 10 spec scenarios:
1. Manual tab renders all fields and controls
2. Manual save calls createUserSkill.mutateAsync with correct payload
3. Manual validation (3 tests): save disabled when name/content empty, inline error on name blur
4. AI tab renders description textarea and generate button
5. Tab switching preserves manual form state
6. Template pre-seed opens AI tab with description pre-filled
7. AI generation flow: form -> generating -> preview transitions (deferred promise pattern)
8. Tab triggers disabled during AI generation
9. Modal close triggers onOpenChange
10. Escape key closes modal

### Task 2: Wire SkillAddModal into settings page and deprecate old modal

**Commit:** 58a97625

- Replaced `SkillGeneratorModal` import with `SkillAddModal` in `skills-settings-page.tsx`
- Added `defaultTab={selectedTemplate ? 'ai-generate' : 'manual'}` prop
- Added `@deprecated` JSDoc to `skill-generator-modal.tsx` (file + export function)
- Added `SkillAddModal` and `SkillAddModalProps` exports to `components/index.ts`

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- TypeScript: zero errors (`pnpm tsc --noEmit`)
- ESLint: zero errors, only pre-existing warnings in unrelated files
- Tests: 12/12 pass (`pnpm vitest run src/features/settings/components/__tests__/skill-add-modal.test.tsx`)
- File size: 682 lines (under 700 limit)
- Pre-commit hooks: all pass

## Self-Check: PASSED

- [x] `frontend/src/features/settings/components/skill-add-modal.tsx` exists (682 lines)
- [x] `frontend/src/features/settings/components/__tests__/skill-add-modal.test.tsx` exists (346 lines)
- [x] Commit 1558e4b7 exists (Task 1)
- [x] Commit 58a97625 exists (Task 2)
- [x] `skills-settings-page.tsx` imports SkillAddModal (not SkillGeneratorModal)
- [x] `skill-generator-modal.tsx` has @deprecated JSDoc
- [x] `index.ts` exports SkillAddModal

---
phase: 12-onboarding-first-run-ux
plan: "02"
subsystem: frontend/onboarding
tags: [onboarding, ux, api-key, toast, settings-links, ONBD-03, ONBD-04, ONBD-05]
dependency_graph:
  requires:
    - 12-01  # WorkspaceContext UUID fix — workspaceId is now always a UUID
  provides:
    - inline-api-key-setup  # ApiKeySetupStep component
    - skill-save-toast      # toast.success('Skill saved and active')
    - settings-links        # Go to settings link per incomplete step
  affects:
    - onboarding-checklist  # OnboardingChecklist wires inline expansion
    - onboarding-step-item  # OnboardingStepItem gains settingsHref prop
tech_stack:
  added: []
  patterns:
    - "Inline expansion below checklist item (no navigation)"
    - "Secondary settings link via optional prop on step item"
    - "toast.success in mutation onSuccess before cache invalidation"
key_files:
  created:
    - frontend/src/features/onboarding/components/ApiKeySetupStep.tsx
    - frontend/src/features/onboarding/components/__tests__/ApiKeySetupStep.test.tsx
    - frontend/src/features/onboarding/__tests__/OnboardingChecklist.test.tsx
  modified:
    - frontend/src/features/onboarding/components/OnboardingChecklist.tsx
    - frontend/src/features/onboarding/components/OnboardingStepItem.tsx
    - frontend/src/features/onboarding/hooks/useRoleSkillActions.ts
    - frontend/vitest.config.ts
decisions:
  - "ApiKeySetupStep renders inline (no navigation) — removes context switch from onboarding flow"
  - "STEP_SETTINGS_PATH map in OnboardingChecklist — avoids prop-drilling the workspaceSlug to OnboardingStepItem just for href construction"
  - "vitest.config.ts env stubs for NEXT_PUBLIC_SUPABASE_URL/ANON_KEY — all tests were blocked by missing env; stubs allow unit tests to import without a live Supabase instance"
metrics:
  duration_minutes: 8
  completed_date: "2026-03-09"
  tasks_completed: 2
  files_changed: 7
---

# Phase 12 Plan 02: Inline API Key Guidance, Skill Save Toast, and Settings Links Summary

**One-liner:** Inline Anthropic API key form with connection test in onboarding checklist, toast confirmation after skill save, and contextual "Go to settings" links per step.

## What Was Built

### ONBD-03: Inline API Key Setup (ApiKeySetupStep)

New `ApiKeySetupStep` component renders below the `ai_providers` checklist item when it is active, replacing the previous navigate-away behavior. The component includes:

- Format hint: "Keys start with `sk-ant-`"
- External link to `https://console.anthropic.com/settings/keys`
- Password input with `sk-ant-...` placeholder
- "Test connection" button — calls `useValidateProviderKey({ provider: 'anthropic', apiKey })`, shows inline "Connected — N models" or error message
- "Open full settings to save your key" fallback button for full settings navigation

`OnboardingChecklist` change: removed `closeModal()` + `router.push()` for the `ai_providers` action; the `ApiKeySetupStep` renders inline via a `React.Fragment` wrapper in the step list.

### ONBD-04: Skill Save Success Toast

`useCreateRoleSkill.onSuccess` now fires `toast.success('Skill saved and active')` before cache invalidation. The `toast` import was already present in the file.

### ONBD-05: Settings Links Per Step

`OnboardingStepItem` gains an optional `settingsHref?: string` prop. When provided and the step is not completed, a 10px "Go to settings" anchor renders below the description.

`OnboardingChecklist` defines a `STEP_SETTINGS_PATH` map:
- `ai_providers` → `settings/ai-providers`
- `invite_members` → `settings/members`
- `role_setup` → `settings/skills`
- `first_note` — intentionally omitted (no settings page)

The checklist constructs full hrefs at render time using `/${workspaceSlug}/${settingsPath}`.

## Tests

| Test File | Tests | Result |
|-----------|-------|--------|
| `ApiKeySetupStep.test.tsx` | 10 | GREEN |
| `OnboardingChecklist.test.tsx` | 7 | GREEN |
| `RoleSelectorStep.test.tsx` | 21 | GREEN (pre-existing, now unblocked) |
| `SkillGenerationWizard.test.tsx` | 18 | GREEN (pre-existing, now unblocked) |
| `useRoleSkillActions.test.ts` | 8 | GREEN (pre-existing, now unblocked) |
| **Total** | **64** | **ALL GREEN** |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added NEXT_PUBLIC_SUPABASE env stubs to vitest.config.ts**
- **Found during:** Task 1 test run
- **Issue:** All onboarding tests (pre-existing and new) were blocked with "Missing env.NEXT_PUBLIC_SUPABASE_URL" because vitest does not load `.env.local` by default, and `src/lib/supabase.ts` throws on import without the env var
- **Fix:** Added `env: { NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY }` stubs to `vitest.config.ts`. The stubs are development placeholder values — no real Supabase connection is made in unit tests since all supabase-dependent modules are mocked at the test level
- **Files modified:** `frontend/vitest.config.ts`
- **Commit:** f5ec77f5

**2. [Rule 1 - Bug] Changed `as ReturnType<...>` to `as unknown as ReturnType<...>` in tests**
- **Found during:** Task 1 test commit (pre-commit TypeScript hook)
- **Issue:** Partial mock objects (only `{ mutate, isPending, data }`) could not be directly cast to the full `UseMutationResult` type because they were missing many required fields
- **Fix:** Used `as unknown as ReturnType<...>` double assertion (standard pattern for test partial mocks)
- **Files modified:** `ApiKeySetupStep.test.tsx`
- **Commit:** f5ec77f5

## Self-Check

Files exist:
- [x] `frontend/src/features/onboarding/components/ApiKeySetupStep.tsx`
- [x] `frontend/src/features/onboarding/components/__tests__/ApiKeySetupStep.test.tsx`
- [x] `frontend/src/features/onboarding/__tests__/OnboardingChecklist.test.tsx`

Commits exist:
- [x] f5ec77f5 — Task 1: ApiKeySetupStep + vitest env fix
- [x] 5dbf2078 — Task 2: wire inline + settings links + toast

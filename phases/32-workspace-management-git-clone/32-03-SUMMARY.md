---
phase: 32-workspace-management-git-clone
plan: "03"
subsystem: tauri-frontend-settings
tags: [tauri, settings, git-credentials, folder-picker, desktop, react, typescript]
dependency_graph:
  requires: [32-01, 32-02]
  provides: [desktop-settings-page, settings-modal-desktop-section]
  affects: [settings-modal, tauri-ipc-wrappers]
tech_stack:
  added: []
  patterns:
    - Lazy-loaded settings page via React.lazy + Suspense
    - isTauri() module-level conditional for Tauri-only nav items
    - PAT never pre-populated — empty input with placeholder for update
    - useCallback + useEffect for IPC wrapper side effects
    - Named export convention matching all other settings pages
key_files:
  created:
    - frontend/src/features/settings/pages/desktop-settings-page.tsx
  modified:
    - frontend/src/features/settings/settings-modal-context.tsx
    - frontend/src/features/settings/settings-modal.tsx
decisions:
  - "DesktopSettingsPage is NOT wrapped in observer() — no MobX observables consumed; plain React state via useState/useCallback is sufficient"
  - "settingsNavSections computed at module level via isTauri() — avoids React state/effect for a static check; aligns with Phase 031 decision that isTauri() is safe at module level"
  - "Desktop nav section appended as third NavSection group — keeps Workspace and Account sections unchanged, Desktop group clearly separate"
  - "PAT input always starts empty with placeholder distinguishing 'new' vs 'update' state — credentials.has_pat drives placeholder text"
  - "Reset to default calls setProjectsDir('') then reloads path — Rust backend resolves the actual default path, frontend always shows resolved value"
metrics:
  duration_seconds: 327
  completed_date: "2026-03-20"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 2
---

# Phase 32 Plan 03: Desktop Settings Page — Project Directory + Git Credentials Summary

**One-liner:** DesktopSettingsPage with native folder picker for base directory and OS-keychain-backed git credential form, wired into Settings modal sidebar as a Tauri-only section using isTauri() module-level guard.

## What Was Built

### desktop-settings-page.tsx

Two-section settings page following the `workspace-general-page.tsx` layout convention:

**Section 1: Project Directory**
- Readonly `Input` showing the current base path, loaded via `getProjectsDir()` on mount
- "Change..." button opens native folder picker via `openFolderDialog()` IPC wrapper; on selection calls `setProjectsDir(path)` and updates displayed path
- "Reset to default" link calls `setProjectsDir('')` then reloads the resolved path from Rust
- Inline success ("Saved" with check icon) and error feedback
- Uses `Separator` between sections per existing page convention

**Section 2: Git Credentials**
- Status card showing username + PAT configured status from `getGitCredentials()` — `has_pat: boolean` only, actual PAT never returned
- Username `Input` (pre-filled from existing credentials for convenience)
- PAT `Input` with `type="password"`, always starts empty (never pre-populated), eye-icon visibility toggle
- PAT placeholder: "Enter new PAT to update" when credentials exist, "Enter your Personal Access Token" otherwise
- "Save Credentials" button calls `setGitCredentials(username, pat)`, clears PAT field on success, refreshes status

### settings-modal-context.tsx

Added `'desktop'` to `SettingsSection` union type — extends the 14-member type to 15.

### settings-modal.tsx

Three changes:
1. Added `Monitor` to lucide-react import set
2. Added lazy import for `DesktopSettingsPage`
3. Imported `isTauri` from `@/lib/tauri`
4. Replaced static `settingsNavSections` constant with conditional: appends a "Desktop" `NavSection` with `{ id: 'desktop', label: 'Desktop', icon: Monitor }` only when `isTauri()` returns true
5. Added `desktop: DesktopSettingsPage` to `SECTION_COMPONENTS` Record — required by TypeScript for exhaustive coverage of the updated `SettingsSection` type

The mobile `<select>` automatically includes the Desktop option because it iterates `settingsNavSections` directly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] tauri.ts IPC wrappers already present from Plan 32-02 partial execution**
- **Found during:** Task 1 setup
- **Issue:** The plan interfaces stated these functions "from Plan 02" would need to be added, but tauri.ts already contained all required wrappers (`getProjectsDir`, `setProjectsDir`, `openFolderDialog`, `getGitCredentials`, `setGitCredentials`) — Plan 32-02 had been executed but not documented with a SUMMARY
- **Fix:** No fix needed — immediately proceeded to create `desktop-settings-page.tsx` using the already-present wrappers
- **Impact:** None — time saved

## Verification Results

```
pnpm type-check: Passed (0 errors)
grep 'desktop' settings-modal-context.tsx: | 'desktop'; ✓
grep 'DesktopSettingsPage' settings-modal.tsx: lazy import + SECTION_COMPONENTS entry ✓
grep 'isTauri' settings-modal.tsx: import + module-level conditional ✓
grep 'Monitor' settings-modal.tsx: icon import + nav item ✓
PAT security: type="password", never pre-populated, has_pat only from Rust ✓
```

## Self-Check: PASSED

- frontend/src/features/settings/pages/desktop-settings-page.tsx: FOUND
- frontend/src/features/settings/settings-modal-context.tsx (contains 'desktop'): FOUND
- frontend/src/features/settings/settings-modal.tsx (contains DesktopSettingsPage): FOUND
- Commit 6bb9e4c9: FOUND
- Commit 63a492e3: FOUND

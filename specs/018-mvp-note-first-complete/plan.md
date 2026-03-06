# Implementation Plan: MVP-018 Note-First Complete

**Spec**: `specs/018-mvp-note-first-complete/spec.md`
**Branch**: `018-mvp-note-first-complete`
**Created**: 2026-02-20
**Updated**: 2026-03-06 (v3 — SDLC phase-driven plan with gap closure)

---

## Key Context

### What's Changed Since v2

- **P0 bug fixes completed** (7/7 critical bugs resolved, commit `11f0d2fd`)
- **Members page migrated** to sidebar with role-based write guards (commit `c48e82a7`)
- **Responsive layout fixed** across all sidebar pages (commit `82c40faa`)
- **CI/security fixes** — nightly tests, conftest PostgreSQL support, tool injection sanitization (commit `48034105`)
- **SDLC coverage analysis** completed — identified gaps in Testing (60%), Deployment (40%), Maintenance (65%)

### Codebase Maturity

200+ frontend components, 51 backend routers (150+ endpoints), 41 DB models, 24 AI skills, 33 MCP tools, 13 TipTap extensions. The platform is feature-rich but has **wiring gaps** (dead code) and **SDLC phase gaps** (Testing, Deployment, Maintenance).

---

## Phase Overview

| Phase | Priority | Focus | FRs | Effort |
|---|---|---|---|---|
| 1: Note-First Core Loop | P1 | Wire the core note → issue → AI context pipeline | FR-008 to FR-020 | 3 days |
| 2: Wire Dead Features | P2 | Connect TemplatePicker, Cmd+K, filters, notifications | FR-021 to FR-025 | 2 days |
| 3: SDLC Testing Phase | P2 | CI status on issues, PR review findings in timeline | FR-026 to FR-028 | 2 days |
| 4: SDLC Deployment Phase | P2 | Release notes, export, deployment activity | FR-029 to FR-031 | 2 days |
| 5: SDLC Maintenance Phase | P2 | Notification pipeline, notification center | FR-032 to FR-034 | 3 days |
| 6: Settings & Polish | P3 | Invite flow, AI providers, edge cases | FR-035 to FR-036 | 1 day |

**Total**: ~13 days across 6 phases.

---

## Phase 1: Note-First Core Loop (P1)

The core differentiator pipeline. All pieces exist — this is wiring + verification.

### 1.1 Homepage Activity Feed + AI Digest (FR-008, FR-009, FR-021)

**Existing**: `ActivityFeed/` directory, `DigestPanel/` component, backend `homepage_router`, `DigestWorker`.

**Wire**:
- Verify ActivityFeed fetches from homepage endpoint and groups by date (Today/Yesterday/This Week)
- Wire note content previews (first 2 lines from TipTap JSON → plaintext) on cards
- Verify DigestPanel fetches digest data and renders workspace health metrics
- Add fallback stats when no AI digest available

**Files**:
- `frontend/src/features/homepage/components/ActivityFeed/`
- `frontend/src/features/homepage/components/DigestPanel/`
- `frontend/src/app/(workspace)/[workspaceSlug]/page.tsx`
- `backend/src/pilot_space/api/v1/routers/homepage.py`

---

### 1.2 Note Editor — Slash Commands, Toolbar, Auto-save (FR-010, FR-011, FR-012)

**Existing**: `SlashCommandExtension.ts`, `slash-command-items.ts`, 13 TipTap extensions, NoteStore with `isSaving`/`lastSavedAt`/`hasUnsavedChanges`.

**Verify**:
- SlashCommand included in `createEditorExtensions()` with 8+ block types
- BubbleMenu configured with Bold, Italic, Strikethrough, Code, Link, Highlight
- Auto-save reaction fires at 2s debounce
- SaveStatus component rendered in editor header

**Files**:
- `frontend/src/features/notes/editor/extensions/slash-command-items.ts`
- `frontend/src/features/notes/editor/extensions/createEditorExtensions.ts`
- `frontend/src/components/editor/` — BubbleMenu/FloatingToolbar, SaveStatus
- `frontend/src/stores/features/notes/NoteStore.ts`

---

### 1.3 Intent Extraction + Issue Creation (FR-013, FR-014, FR-015)

**Existing**: Backend `ai_extraction_router`, `intents_router`, `workspace_note_issue_links_router`. Frontend `InlineIssueExtension.ts`, `InlineIssueComponent.tsx`.

**Wire**:
- Verify extraction endpoint works (note content → categorized intents)
- Verify "Extract issues" trigger exists in editor UI (add toolbar button if missing)
- Wire approval flow: extract → display categorized intents → approve → create issue + NoteIssueLink
- After extraction approval, insert inline badges at extraction points
- Verify clicking badge navigates to issue detail

**Files**:
- `backend/src/pilot_space/api/v1/routers/ai_extraction.py`
- `backend/src/pilot_space/api/v1/routers/intents.py`
- `frontend/src/features/notes/editor/extensions/InlineIssueExtension.ts`
- `frontend/src/features/notes/editor/extensions/InlineIssueComponent.tsx`

---

### 1.4 AI Context + Copy for Claude Code (FR-016, FR-017)

**Existing**: `ai-context-panel.tsx`, `ai-context-tab.tsx`, `claude-code-prompt-card.tsx`, `copy-context.ts`. Backend `issues_ai_context_router`.

**Verify**:
- Context includes 5 sections (description, criteria, requirements, notes, dependencies)
- "Copy for Claude Code" formats correctly and copies to clipboard
- Fix rendering/data issues

**Files**:
- `frontend/src/features/issues/components/ai-context-panel.tsx`
- `frontend/src/features/issues/components/claude-code-prompt-card.tsx`
- `frontend/src/lib/copy-context.ts`
- `backend/src/pilot_space/api/v1/routers/issues_ai_context.py`

---

### 1.5 Kanban Polish — Drag-Drop, Cards, Views (FR-018, FR-019, FR-020)

**Existing**: Issue components, IssueStore with `viewMode`, dnd-kit likely in package.json.

**Verify/Fix**:
- Drag-and-drop works between Kanban columns → state update
- Issue cards show: identifier, title, priority color indicator, assignee avatar
- List and Table views render and function
- Table has sortable columns

**Files**:
- `frontend/src/features/issues/components/` — board, list, table components
- `frontend/src/app/(workspace)/[workspaceSlug]/issues/page.tsx`

---

## Phase 2: Wire Dead Features (P2)

### 2.1 TemplatePicker in New Note Flow (FR-023)

**Existing**: `TemplatePicker` component 100% built with keyboard navigation + TanStack Query. 4 system SDLC templates in backend `note_templates_router`.

**Fix**: Mount TemplatePicker in the "New Note" creation flow. When user clicks "New Note", show TemplatePicker instead of creating blank note directly.

**Files**:
- Find "New Note" trigger (sidebar or notes page)
- `frontend/src/features/notes/components/TemplatePicker.tsx` (or similar)
- `backend/src/pilot_space/api/v1/routers/note_templates.py`

---

### 2.2 Cmd+K Global Search (FR-024)

**Existing**: UIStore `commandPaletteOpen` state, Meilisearch indexes notes + issues.

**Build**:
- Create SearchModal component (or find existing)
- Wire Cmd+K shortcut to toggle `commandPaletteOpen`
- Connect to Meilisearch for note body + issue search
- Navigate to result on selection

**Files**:
- `frontend/src/stores/UIStore.ts`
- `frontend/src/components/` — new or existing SearchModal
- Meilisearch client config

---

### 2.3 Issue Filter Dropdowns (FR-025)

**Existing**: Assignee/Label filter dropdowns exist but render empty arrays.

**Fix**: Wire dropdown options to fetch actual workspace members and project labels.

**Files**:
- `frontend/src/features/issues/components/` — filter components
- `frontend/src/services/api/` — members and labels API calls

---

### 2.4 Version History (FR-022)

**Existing**: `VersionHistoryPanel.tsx`, `useNoteVersions.ts`, `versionApi.ts`. Backend `note_versions_router`.

**Verify**: List → view → restore flow works. Fix data binding issues.

**Files**:
- `frontend/src/components/editor/VersionHistoryPanel.tsx`
- `frontend/src/hooks/useNoteVersions.ts`
- `frontend/src/features/notes/services/versionApi.ts`

---

## Phase 3: SDLC Testing Phase Gap (P2)

Target: 60% → 70% coverage.

### 3.1 CI Status on Issues (FR-026)

**Existing**: GitHub webhook receives PR events. `IssueGitHubPRLink` tracks PR-to-issue links. PR data stored in backend.

**Build**:
- Extract CI check status from GitHub webhook `check_suite` / `check_run` events
- Store latest CI status per PR link
- Display CI badge (pass/fail/pending) on issue detail next to linked PR
- Expose via `GET /issues/{id}/github-links` response enrichment

**Files**:
- `backend/src/pilot_space/api/v1/routers/github_links.py`
- `backend/src/pilot_space/services/github/` — webhook handler
- `frontend/src/features/issues/components/` — PR link display

---

### 3.2 PR Review Findings in Issue Timeline (FR-027)

**Existing**: `PRReviewSubagent` posts comments to GitHub PR. Issue activity timeline exists.

**Wire**:
- When PR review completes, create activity entry on linked issue
- Show severity summary (Critical: N, Warning: N, Info: N) in timeline card
- Link to full PR review on GitHub

**Files**:
- `backend/src/pilot_space/ai/agents/` — PR review completion hook
- `backend/src/pilot_space/api/v1/routers/` — issue activity router
- `frontend/src/features/issues/components/` — activity timeline card

---

### 3.3 Project Quality Dashboard (FR-028) — MAY

**Build** (if time permits):
- Aggregate: open PRs with review status, recent CI failures, linked issues by state
- Display on project overview page
- Pull data from existing GitHub link + PR review tables

---

## Phase 4: SDLC Deployment Phase Gap (P2)

Target: 40% → 65% coverage.

### 4.1 Release Notes per Cycle (FR-029)

**Existing**: Backend `pm_release_notes_router` with heuristic classifier (categorizes issues as features/bug_fixes/improvements/internal). `ReleaseNotesResponse` schema exists.

**Wire**:
- Add "Release Notes" tab to cycle detail page
- Fetch auto-categorized completed issues via existing endpoint
- Display grouped by category with human-edit capability

**Files**:
- `backend/src/pilot_space/api/v1/routers/pm_release_notes.py`
- `frontend/src/features/cycles/` — cycle detail page
- New: release notes tab component

---

### 4.2 Release Notes Export (FR-030)

**Build**:
- Add "Export as Markdown" button to release notes tab
- Format as GitHub Release-compatible markdown
- Copy to clipboard or download as `.md` file

---

### 4.3 Deployment Activity in Issue Timeline (FR-031) — MAY

**Wire** (if time permits):
- On PR merge webhook event, create activity entry showing merge commit + target branch
- Display in issue timeline as "Deployed to main" or similar

---

## Phase 5: SDLC Maintenance Phase Gap (P2)

Target: 65% → 80% coverage.

### 5.1 Notification Backend Pipeline (FR-032)

**Existing**: `QueueName.NOTIFICATIONS` queue, `enqueue_notification()` function, `NotificationStore` UI.

**Build**:
- Create `notifications` table migration (user_id, workspace_id, type, title, body, entity_type, entity_id, read_at, priority, created_at)
- Create notification service with CRUD operations
- Create notification worker consuming from pgmq queue
- Emit notifications for: PR review complete, issue assignment change, sprint deadline warning

**Files**:
- `backend/src/pilot_space/models/` — new notification model
- `backend/src/pilot_space/services/` — notification service
- `backend/src/pilot_space/workers/` — notification worker
- `backend/src/pilot_space/api/v1/routers/` — notification router

---

### 5.2 Notification Center Frontend (FR-033)

**Existing**: `NotificationStore` with bell icon, priority badges, mark-as-read UI.

**Wire**:
- Connect NotificationStore to backend notification endpoint
- Fetch notifications on mount + SSE for real-time updates
- Group by type, show priority badges
- Mark-as-read on click

**Files**:
- `frontend/src/stores/` — NotificationStore
- `frontend/src/components/` — notification bell, notification panel

---

### 5.3 Notification Preferences (FR-034) — MAY

**Build** (if time permits):
- Per-user notification preferences: enable/disable per type, in-app only
- Settings page section for notification preferences

---

## Phase 6: Settings & Polish (P3)

### 6.1 Fix Invitation Flow (FR-035)

**Known bug**: "Invite Members" dispatches CustomEvent with no listener.

**Fix**: Replace CustomEvent with direct API call to invitation endpoint.

**Files**:
- `frontend/src/app/(workspace)/[workspaceSlug]/settings/members/page.tsx`
- `backend/src/pilot_space/api/v1/routers/workspace_invitations.py`

---

### 6.2 Fix AI Providers Error Display (FR-036)

**Known bug**: Shows `[object Object]` error instead of meaningful message.

**Fix**: Serialize error object to readable string.

**Files**:
- `frontend/src/app/(workspace)/[workspaceSlug]/settings/ai-providers/page.tsx`

---

## Cross-Cutting Notes

### SDLC Coverage Targets After Plan Execution

| Phase | Before | After | Delta |
|---|---|---|---|
| Planning | 75% | 75% | — (no changes needed) |
| Requirements | 85% | 85% | — (already strong) |
| Design | 80% | 80% | — (KG viz deferred to v2.1) |
| Implementation | 85% | 90% | +5% (dead code wired) |
| Testing | 60% | 70% | +10% (CI status, PR findings) |
| Deployment | 40% | 65% | +25% (release notes, export) |
| Maintenance | 65% | 80% | +15% (notifications pipeline) |

### Dependencies Graph

```
Phase 1 (P1 — all can run in parallel):
  1.1 Homepage Feed + Digest
  1.2 Editor Verification
  1.3 Intent Extraction Pipeline
  1.4 AI Context Verification
  1.5 Kanban Polish

Phase 2 (P2 — independent of Phase 1):
  2.1 TemplatePicker
  2.2 Cmd+K Search
  2.3 Issue Filters
  2.4 Version History

Phase 3 (P2 — depends on GitHub integration):
  3.1 CI Status on Issues
  3.2 PR Review in Timeline ← depends on 3.1
  3.3 Quality Dashboard ← depends on 3.1, 3.2

Phase 4 (P2 — independent):
  4.1 Release Notes Tab
  4.2 Release Notes Export ← depends on 4.1
  4.3 Deployment Activity

Phase 5 (P2 — sequential):
  5.1 Notification Backend ← blocks 5.2
  5.2 Notification Center ← depends on 5.1
  5.3 Notification Preferences ← depends on 5.2

Phase 6 (P3 — independent):
  6.1 Invitation Flow Fix
  6.2 AI Providers Fix
```

### Execution Strategy

```
Week 1: Phase 1 (all 5 items parallel) + Phase 6 (quick fixes)
Week 2: Phase 2 (all 4 items parallel) + Phase 3 (3.1 → 3.2)
Week 3: Phase 4 (4.1 → 4.2) + Phase 5 (5.1 → 5.2)
```

### Testing Strategy

- Unit tests for each new feature/fix
- Integration tests for notification pipeline (backend)
- Smoke test per phase: verify core flow end-to-end
- Quality gates before each commit: `make quality-gates-backend` + `make quality-gates-frontend`

# Task Breakdown: MVP-018 Note-First Complete

**Plan**: `specs/018-mvp-note-first-complete/plan.md`
**Branch**: `018-mvp-note-first-complete`
**Created**: 2026-02-20
**Updated**: 2026-03-06 (v3 — SDLC phase-driven tasks with gap closure)

---

## Summary

| Phase | Tasks | Status | Effort |
|---|---|---|---|
| 0: Bug Fixes (P0) | T-001 to T-007 | COMPLETED | — |
| 1: Note-First Core Loop (P1) | T-008 to T-017 | Partially Done | — |
| 2: Wire Dead Features (P2) | T-018 to T-022 | Partially Done | — |
| 3: SDLC Testing Phase (P2) | T-023 to T-025 | Pending | 2 days |
| 4: SDLC Deployment Phase (P2) | T-026 to T-028 | Pending | 2 days |
| 5: SDLC Maintenance Phase (P2) | T-029 to T-032 | Pending | 3 days |
| 6: Settings & Polish (P3) | T-033 to T-034 | COMPLETED | — |

**Total**: 34 tasks. 7 completed, 27 pending. ~13 days remaining.

---

## Phase 0: Bug Fixes (P0) — COMPLETED

### T-001: Fix Issues Kanban state mapping (FR-001) — DONE
### T-002: Fix AI Chat 404 error (FR-002) — DONE
### T-003: Fix Approvals "Bad Request" (FR-003) — DONE
### T-004: Fix Costs "Not Found" (FR-004) — DONE
### T-005: Fix Homepage note word counts (FR-005) — DONE
### T-006: Fix Issue Detail "null pts" / "No priority" (FR-006) — DONE
### T-007: Fix Sidebar PINNED/RECENT empty (FR-007) — DONE

---

## Phase 1: Note-First Core Loop (P1)

### T-008: Wire homepage activity feed with date grouping (FR-008, FR-021)

**Type**: Wiring | **Scope**: Frontend + Backend verification
**Depends on**: None

**Steps**:
1. Read `frontend/src/features/homepage/components/ActivityFeed/` — check existing components
2. Verify ActivityFeed fetches from homepage endpoint
3. Wire date grouping (Today/Yesterday/This Week/Earlier) if not connected
4. Wire note content previews (first 2 lines TipTap → plaintext) on cards

**Files**:
- `frontend/src/features/homepage/components/ActivityFeed/`
- `frontend/src/app/(workspace)/[workspaceSlug]/page.tsx`
- `backend/src/pilot_space/api/v1/routers/homepage.py`

**Acceptance**: Activity grouped by date. Note cards show 2-line previews.

---

### T-009: Wire AI digest panel on homepage (FR-009)

**Type**: Wiring | **Scope**: Frontend + Backend verification
**Depends on**: T-008

**Steps**:
1. Read `DigestPanel/` — check expected data shape
2. Verify backend digest endpoint returns data
3. Add fallback: basic workspace stats when no AI digest

**Files**:
- `frontend/src/features/homepage/components/DigestPanel/`
- `backend/src/pilot_space/api/v1/routers/homepage.py`

**Acceptance**: Insights panel shows workspace health metrics or fallback stats.

---

### T-010: Verify slash commands — 8+ block types (FR-010) — DONE
### T-011: Verify floating toolbar on text selection (FR-011) — DONE (added Strikethrough, Code, Highlight)
### T-012: Verify auto-save and save indicator (FR-012) — DONE (wired in NoteCanvasLayout)
### T-013: Wire intent extraction UI (FR-013, FR-014) — DONE (ExtractionPreviewModal in NoteCanvasLayout)
### T-014: Wire inline issue badges after extraction (FR-015) — DONE (NoteIssueLink invalidation on created)

---

### T-015: Verify AI Context tab renders 5+ sections (FR-016, FR-017) — DONE (CloneContextPanel exports 5 sections)

---

### T-016: Verify Kanban drag-drop and issue card display (FR-018, FR-019)

**Type**: Verification | **Scope**: Frontend

**Steps**:
1. Check `package.json` for dnd-kit or similar
2. Verify drag-and-drop works between columns → state update
3. Verify cards show: identifier, title, priority color, assignee avatar
4. Fix missing elements

**Files**:
- `frontend/src/features/issues/components/` — board component
- `frontend/package.json`

**Acceptance**: Drag-and-drop moves issues between states. Cards show all info.

---

### T-017: Verify List and Table views work (FR-020)

**Type**: Verification | **Scope**: Frontend

**Steps**:
1. Find view mode toggle and list/table components
2. Verify table has sortable columns
3. Fix rendering issues

**Files**:
- `frontend/src/features/issues/components/` — list, table views
- `frontend/src/app/(workspace)/[workspaceSlug]/issues/page.tsx`

**Acceptance**: Three view modes work. Table has sortable columns.

---

## Phase 2: Wire Dead Features (P2)

### T-018: Mount TemplatePicker in "New Note" flow (FR-023) — DONE (wired in sidebar.tsx + notes/page.tsx)

---

### T-019: Build Cmd+K global search modal (FR-024) — DONE (CommandPaletteModal in AppShell)

---

### T-020: Fix issue filter dropdowns — Assignee and Label (FR-025) — DONE (useWorkspaceMembers/useWorkspaceLabels wired)

---

### T-021: Verify version history panel (FR-022)

**Type**: Verification | **Scope**: Frontend + Backend

**Steps**:
1. Read VersionHistoryPanel, useNoteVersions, versionApi
2. Verify list → view → restore flow
3. Fix data binding issues

**Files**:
- `frontend/src/components/editor/VersionHistoryPanel.tsx`
- `frontend/src/hooks/useNoteVersions.ts`
- `frontend/src/features/notes/services/versionApi.ts`

**Acceptance**: Version list shows timestamps. Restore replaces editor content.

---

### T-022: Connect note body search to Meilisearch (FR-024)

**Type**: Wiring | **Scope**: Frontend
**Depends on**: T-019 (shares Meilisearch client)

**Steps**:
1. Find notes list search input
2. Replace client-side title-only filter with Meilisearch query
3. Show "Limited search" indicator if Meilisearch unavailable

**Files**:
- `frontend/src/features/notes/` — notes list page, search input
- Meilisearch client

**Acceptance**: Notes page search queries Meilisearch for body content, not just title.

---

## Phase 3: SDLC Testing Phase (P2)

### T-023: Display CI check status on issues with linked PRs (FR-026)

**Type**: Build | **Scope**: Backend + Frontend

**Steps**:
1. Check GitHub webhook handler for `check_suite` / `check_run` events
2. Store latest CI status (pass/fail/pending) on `IssueGitHubPRLink` or new column
3. Enrich `GET /issues/{id}/github-links` response with CI status
4. Display CI badge (green check / red X / yellow dot) next to PR link in issue detail

**Files**:
- `backend/src/pilot_space/services/github/` — webhook handler
- `backend/src/pilot_space/api/v1/routers/github_links.py`
- `backend/src/pilot_space/models/` — PR link model (add ci_status column if needed)
- `frontend/src/features/issues/components/` — PR link display
- Migration: add `ci_status` column to `issue_github_pr_links`

**Acceptance**: Issue detail shows CI badge next to linked PR. Updates on webhook.

---

### T-024: Surface PR review findings in issue activity timeline (FR-027)

**Type**: Wiring | **Scope**: Backend + Frontend
**Depends on**: T-023

**Steps**:
1. Find PR review completion hook in `PRReviewSubagent`
2. On completion, create activity entry on linked issue with severity summary
3. Display in issue timeline as card with: "AI Review: 2 Critical, 3 Warning, 5 Info"
4. Link to full PR on GitHub

**Files**:
- `backend/src/pilot_space/ai/agents/` — PR review subagent
- `backend/src/pilot_space/api/v1/routers/` — issue activity
- `frontend/src/features/issues/components/` — activity timeline

**Acceptance**: PR review findings appear in issue activity. Severity badge + GitHub link.

---

### T-025: Build project quality dashboard (FR-028) — OPTIONAL

**Type**: Build | **Scope**: Frontend + Backend
**Depends on**: T-023, T-024

**Steps**:
1. Create aggregate endpoint: open PRs with review status, recent CI failures
2. Display on project overview or dashboard page
3. Show: PR review pass rate, CI success rate, issues by state

**Acceptance**: Project page shows quality metrics section.

---

## Phase 4: SDLC Deployment Phase (P2)

### T-026: Wire release notes tab on cycle detail page (FR-029)

**Type**: Wiring | **Scope**: Frontend

**Steps**:
1. Read `pm_release_notes_router` — verify endpoint works
2. Add "Release Notes" tab to cycle detail page
3. Fetch auto-categorized completed issues
4. Display grouped by category (Features, Bug Fixes, Improvements, Internal)

**Files**:
- `backend/src/pilot_space/api/v1/routers/pm_release_notes.py`
- `frontend/src/features/cycles/` — cycle detail page
- New: release notes tab component

**Acceptance**: Cycle detail shows "Release Notes" tab with categorized issues.

---

### T-027: Add release notes markdown export (FR-030)

**Type**: Build | **Scope**: Frontend
**Depends on**: T-026

**Steps**:
1. Add "Export as Markdown" button to release notes tab
2. Format as GitHub Release-compatible markdown:
   ```
   ## v{version} — {cycle_name}
   ### Features
   - {issue_ref}: {title}
   ### Bug Fixes
   - {issue_ref}: {title}
   ```
3. Copy to clipboard and/or download as `.md`

**Acceptance**: Export produces clean markdown. Clipboard copy works.

---

### T-028: Show deployment activity in issue timeline (FR-031) — OPTIONAL

**Type**: Wiring | **Scope**: Backend + Frontend

**Steps**:
1. On PR merge webhook, create activity entry on linked issue
2. Display: "Merged to main" with commit SHA and branch

**Acceptance**: PR merge appears in issue timeline.

---

## Phase 5: SDLC Maintenance Phase (P2)

### T-029: Create notification model and migration

**Type**: Build | **Scope**: Backend

**Steps**:
1. Create `Notification` SQLAlchemy model:
   - `id`, `user_id`, `workspace_id`, `type` (enum: pr_review, assignment, sprint_deadline, mention, general)
   - `title`, `body`, `entity_type`, `entity_id`
   - `priority` (enum: low, medium, high, urgent)
   - `read_at` (nullable), `created_at`
2. Create Alembic migration
3. Add RLS policy: users see only their own notifications
4. Create notification CRUD service

**Files**:
- `backend/src/pilot_space/models/` — new notification model
- `backend/alembic/versions/` — new migration
- `backend/src/pilot_space/services/` — notification service

**Acceptance**: Migration runs. CRUD service passes unit tests.

---

### T-030: Build notification worker and router (FR-032)

**Type**: Build | **Scope**: Backend
**Depends on**: T-029

**Steps**:
1. Create notification worker consuming from `QueueName.NOTIFICATIONS` pgmq queue
2. Worker creates `Notification` records from queue messages
3. Create REST router: `GET /notifications` (paginated), `PATCH /notifications/{id}/read`, `POST /notifications/read-all`
4. Emit notifications for:
   - PR review complete → PR author + issue assignee
   - Issue assignment change → new assignee
   - Sprint deadline warning (2 days remaining) → assignees of incomplete issues

**Files**:
- `backend/src/pilot_space/workers/` — notification worker
- `backend/src/pilot_space/api/v1/routers/` — notification router
- Integration points in PR review, issue assignment, sprint check

**Acceptance**: Notifications created from queue. REST API returns paginated notifications.

---

### T-031: Wire notification center frontend (FR-033)

**Type**: Wiring | **Scope**: Frontend
**Depends on**: T-030

**Steps**:
1. Connect existing `NotificationStore` to backend notification endpoint
2. Fetch notifications on mount
3. Wire SSE or polling for real-time updates
4. Group notifications by type with priority badges
5. Mark-as-read on click, bulk mark-all-read

**Files**:
- `frontend/src/stores/` — NotificationStore
- `frontend/src/components/` — notification bell, panel

**Acceptance**: Bell icon shows unread count. Panel shows grouped notifications. Mark-as-read works.

---

### T-032: Add notification preferences (FR-034) — OPTIONAL

**Type**: Build | **Scope**: Frontend + Backend
**Depends on**: T-031

**Steps**:
1. Add preferences model (per-user, per-notification-type enable/disable)
2. Add preferences section to Settings page
3. Notification worker checks preferences before creating

**Acceptance**: User can disable notification types. Disabled types not created.

---

## Phase 6: Settings & Polish (P3)

### T-033: Fix workspace invitation flow (FR-035) — DONE (members page redirects to /members which has InviteMemberDialog)

---

### T-034: Fix AI Providers error display (FR-036) — DONE (ai-settings-page.tsx properly renders error.message)

---

## Dependencies Graph

```
Phase 0: COMPLETED (T-001 to T-007)

Phase 1 (P1 — mostly parallel):
  T-008 → T-009
  T-010, T-011, T-012 (independent)
  T-013 → T-014
  T-015, T-016, T-017 (independent)

Phase 2 (P2 — mostly parallel):
  T-018, T-020, T-021 (independent)
  T-019 → T-022

Phase 3 (P2 — sequential):
  T-023 → T-024 → T-025 (optional)

Phase 4 (P2 — sequential):
  T-026 → T-027
  T-028 (optional, independent)

Phase 5 (P2 — sequential):
  T-029 → T-030 → T-031 → T-032 (optional)

Phase 6 (P3 — independent):
  T-033, T-034
```

## Execution Plan

```
Week 1 (P1):
  Day 1: T-008, T-010, T-011, T-012, T-033, T-034 (parallel — homepage, editor, settings)
  Day 2: T-009, T-013, T-015, T-016 (parallel — digest, extraction, AI context, kanban)
  Day 3: T-014, T-017, T-018 (parallel — badges, views, templates)

Week 2 (P2 — Dead Features + Testing):
  Day 4: T-019, T-020, T-021 (parallel — Cmd+K, filters, versions)
  Day 5: T-022, T-023 (parallel — Meilisearch, CI status)
  Day 6: T-024, T-026 (parallel — PR findings, release notes)

Week 3 (P2 — Deployment + Maintenance):
  Day 7: T-027, T-029 (parallel — export, notification model)
  Day 8: T-030 (notification worker + router)
  Day 9: T-031 (notification frontend)
  Day 10+: T-025, T-028, T-032 (optional stretch tasks)
```

## SDLC Coverage Impact

| Phase | Before | After | Tasks Driving Change |
|---|---|---|---|
| Planning | 75% | 75% | — |
| Requirements | 85% | 85% | — |
| Design | 80% | 80% | — |
| Implementation | 85% | 90% | T-018 (templates), T-019 (Cmd+K), T-022 (search) |
| Testing | 60% | 70% | T-023 (CI status), T-024 (PR findings) |
| Deployment | 40% | 65% | T-026 (release notes), T-027 (export) |
| Maintenance | 65% | 80% | T-029–T-031 (notifications pipeline) |

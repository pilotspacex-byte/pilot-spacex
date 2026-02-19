# Implementation Plan: Note Versioning & PM Blocks

**Feature Number**: 017
**Spec Version**: v1.0
**Created**: 2026-02-19
**Author**: Tin Dang

---

## Overview

2 sprints delivering M6c (Version Engine) → M6d (PM Block Engine). M6c depends on Feature 016's CRDT for version restore during collaboration and Ownership Engine for PM block edit guards. M6d depends on M6c for before/after versioning of AI operations.

**Critical path**: M6c (Version Engine) → M6d (PM Block Engine)

**Migration base**: Continues from Feature 016 (migration 041). Feature 017 starts at 042.

**Dependency**: Feature 016 must be complete (CRDT for collaborative restore, Ownership for edit guards on PM blocks).

---

## Sprint 1: Version Engine (M6c)

**Goal**: Point-in-time note snapshots with auto/manual save, visual diff, non-destructive restore, and AI-powered change digest.

### Phase 1a: Database + Domain

| Deliverable | Layer | Details |
|-------------|-------|---------|
| Migration 042: `note_versions` table | DB | UUID PK, note_id FK, workspace_id (RLS), trigger enum (auto/manual/ai_before/ai_after), content JSONB (full TipTap doc), label varchar(255) nullable, pinned boolean (default false), digest text nullable (AI summary), digest_cached_at timestamp nullable, created_by UUID FK, created_at. Index on (note_id, created_at DESC). |
| NoteVersion domain entity | BE | Rich entity with: trigger validation, label constraints (max 100 chars), pinned flag, digest cache invalidation logic. Immutable content after creation (snapshots never modified). |
| NoteVersionRepository | BE | Async CRUD + RLS enforcement. Queries: by note_id (paginated, newest first), by trigger type, pinned only. Retention query: find versions exceeding count/age limits (excluding pinned). |
| RLS policies for note_versions | DB | Workspace-scoped via notes join. Member+ read access. Write restricted to system (auto) + member (manual). |

### Phase 1b: Version Service

| Deliverable | Layer | Details |
|-------------|-------|---------|
| VersionSnapshotService | BE | `snapshot(noteId, trigger, label?, createdBy)` → captures current TipTap doc content → creates NoteVersion. For `ai_before`/`ai_after`: called by skill executor before/after execution. |
| Auto-version scheduler | BE | Background timer: snapshot every 5 minutes of active editing (FR-034). "Active editing" = at least 1 edit event in window. Uses note metadata `last_edit_at` to determine activity. |
| Auto-version via pg_cron | DB | SQL function `fn_auto_version_active_notes()`: finds notes with `last_edit_at > now() - interval '5 minutes'` and no version in last 5 minutes → enqueues snapshot job to `ai_normal` queue. Scheduled every 5 min. |
| VersionDiffService | BE | `diff(v1Id, v2Id)` → loads both versions' JSONB content → produces block-level diff (added, removed, modified blocks). Returns structured diff result for frontend rendering. |
| VersionRestoreService | BE | `restore(versionId)` → creates new version with trigger "manual" + label "Restored from {original_label or timestamp}" → replaces current note content. Non-destructive: original version preserved (FR-039). If CRDT active: applies as Yjs transaction. |
| VersionDigestService | AI | `digest(versionId)` → compares version to previous version → calls LLM (Sonnet) for human-readable summary of changes. Cached in `note_versions.digest`. Cache invalidated when linked entities (issues, annotations) change (FR-042). <3s for 95% (FR-040). |
| ImpactAnalysisService | AI | `impact(versionId)` → scans version content for entity references (issue IDs, note links) → lists affected entities with change type (created, modified, removed) (FR-041). |
| RetentionService | BE | `cleanup(noteId, maxCount, maxAgeDays)` → deletes versions exceeding limits, excluding pinned versions (FR-074, FR-075). Configurable per workspace. Default: 50 versions, 90 days. |
| Version API router | BE | `POST /api/v1/notes/{id}/versions` (manual snapshot), `GET .../versions` (paginated list), `GET .../versions/{vId}` (single), `GET .../versions/{v1}/diff/{v2}` (diff), `POST .../versions/{vId}/restore`, `GET .../versions/{vId}/digest`, `GET .../versions/{vId}/impact`, `PUT .../versions/{vId}/pin`, `DELETE .../versions/{vId}` (if not pinned). |

### Phase 1c: Version UI

| Deliverable | Layer | Details |
|-------------|-------|---------|
| Version history sidebar panel (full) | FE | Replace Feature 016's placeholder. Shows version list: trigger icon, label, creator avatar, relative time, pinned badge. Infinite scroll. Manual "Save Version" button at top. |
| Visual diff view | FE | Side-by-side or inline diff of two versions. Added blocks: green highlight. Removed blocks: red strikethrough. Modified blocks: yellow highlight with change markers. Block-level granularity. |
| Restore confirmation dialog | FE | "Restore to version from {timestamp}?" with preview. Shows current version vs target. [Restore] creates new version (non-destructive). Loading state during restore. |
| Version digest display | FE | In version list: each version shows AI digest summary (1-2 sentences). Lazy-loaded on expand. "Generating..." spinner if not cached. Impact analysis expandable below digest. |
| Pin/unpin version | FE | Star icon on version entry. Pinned versions show at top of list. Pinned badge. Tooltip: "Pinned versions are exempt from retention cleanup". |

### Sprint 1 Gate

- [ ] Auto-version triggers every 5 minutes of active editing (integration test)
- [ ] Manual "Save Version" creates snapshot on demand (integration test)
- [ ] AI before/after versions created by skill executor (integration test)
- [ ] Visual diff shows block-level changes correctly (unit test + Storybook)
- [ ] Restore creates new version, does not destroy original (integration test)
- [ ] Restore during CRDT collab applies as Yjs transaction (integration test, if CRDT active)
- [ ] AI digest generated <3s for 95% of cases (performance test)
- [ ] Impact analysis lists affected entities accurately >90% (integration test)
- [ ] Retention cleanup respects pinned versions (unit test)
- [ ] Test coverage >80% for new code

---

## Sprint 2: PM Block Engine (M6d)

**Goal**: 4 new PM block types for sprint ceremonies within notes, with AI-powered insights.

**Depends on**: Sprint 1 complete (before/after versioning needed for AI operations on PM blocks). Feature 016 M6b (ownership edit guards for PM blocks).

### Phase 2a: Database + Infrastructure

| Deliverable | Layer | Details |
|-------------|-------|---------|
| Migration 043: `pm_block_insights` table | DB | UUID PK, workspace_id (RLS), block_id varchar (TipTap block reference), block_type enum (sprint_board/dependency_map/capacity_plan/release_notes), insight_type varchar, severity enum (green/yellow/red), title varchar, analysis text, references JSONB, suggested_actions JSONB, confidence float(0-1), dismissed boolean (default false), created_at, updated_at. Index on (block_id, dismissed). |
| Migration 043: add `estimate_hours` to issues | DB | `ALTER TABLE issues ADD COLUMN estimate_hours DECIMAL(6,1) NULL` (FR-061). No backfill needed. |
| Migration 043: add `weekly_available_hours` to workspace_members | DB | `ALTER TABLE workspace_members ADD COLUMN weekly_available_hours DECIMAL(5,1) DEFAULT 40` (FR-062). Backfill existing rows to 40. |
| PMBlockInsight domain entity | BE | Entity with severity parsing (green/yellow/red), confidence validation (0-1), dismissal logic. |
| PMBlockInsightRepository | BE | CRUD + RLS. Queries: by block_id (non-dismissed), by workspace+block_type, by severity. |
| PM block type contract test | QA | Automated test: backend PM block type list == frontend PM block type list (FR-043, FR-044). Fails on divergence. |

### Phase 2b: Sprint Board Block

| Deliverable | Layer | Details |
|-------------|-------|---------|
| SprintBoardBlock TipTap extension | FE | New PM block type: `sprint-board`. Renders 6 state-based lanes matching issue state machine (Backlog, Todo, In Progress, In Review, Done, Cancelled) (FR-049). Connected to cycle data via API. Drag-and-drop between lanes. |
| Sprint board data API | BE | `GET /api/v1/cycles/{id}/board` → returns issues grouped by state for the cycle. `PATCH /api/v1/issues/{id}/state` → already exists, reuse for drag-drop transitions. |
| AI state transition proposals | AI | `proposeTransition(issueId, newState)` → LLM analyzes issue context (description, linked notes, time in current state) → suggests state change with reasoning. Shows [Approve] [Reject] in sprint board (FR-050). Uses DD-003 approval workflow. |
| Sprint board read-only fallback | FE | When CRDT unavailable: sprint board renders read-only with "View only — collaborative editing required for drag-drop" message (FR-060). State changes only via issue detail page. |

### Phase 2c: Dependency Map Block

| Deliverable | Layer | Details |
|-------------|-------|---------|
| DependencyMapBlock TipTap extension | FE | New PM block type: `dependency-map`. Renders DAG of issue dependencies with critical path highlighting (FR-051). Uses d3-dag or dagre for layout. |
| DAG data API | BE | `GET /api/v1/projects/{id}/dependency-graph` → returns nodes (issues) + edges (issue_relations where type=blocks). Includes critical path calculation (longest path). |
| Zoom/pan for large graphs | FE | Zoom (scroll wheel + pinch), pan (drag), fit-to-view button. Performant for 20+ nodes (FR-052). Web worker for layout calculation if >50 nodes (R-010). |
| Circular dependency detection | BE+FE | Backend: detect cycles in dependency graph → return warning. Frontend: show warning badge, render non-cyclic subgraph (edge case). |

### Phase 2d: Capacity Plan + Release Notes Blocks

| Deliverable | Layer | Details |
|-------------|-------|---------|
| CapacityPlanBlock TipTap extension | FE | New PM block type: `capacity-plan`. Table view: team members, available hours (from `weekly_available_hours`), committed hours (sum of assigned issue `estimate_hours`), utilization %. Color coding: green <80%, yellow 80-100%, red >100% (FR-053). |
| Capacity data API | BE | `GET /api/v1/cycles/{id}/capacity` → returns per-member: name, available_hours, committed_hours, utilization. Requires `estimate_hours` on issues + `weekly_available_hours` on members. |
| ReleaseNotesBlock TipTap extension | FE | New PM block type: `release-notes`. Auto-generated from completed issues in cycle (FR-054). AI classification: features, bug fixes, improvements, breaking changes. Editable after generation. |
| Release notes generation | AI | `generateReleaseNotes(cycleId)` → fetch completed issues → LLM classifies each → generates markdown grouped by category. Preserves human edits during regeneration (FR-055): diff previous generated vs current, merge human edits. Confidence <0.3 → "Uncategorized" (edge case). |
| Estimate hours UI | FE | Add `estimate_hours` field to issue detail page. Decimal input (0.5 increments). Used by capacity plan. |
| Weekly available hours UI | FE | Add `weekly_available_hours` field to workspace member settings. Decimal input. Default 40. |

### Phase 2e: AI Insight Badges

| Deliverable | Layer | Details |
|-------------|-------|---------|
| InsightBadge component | FE | Badge overlay on PM blocks: green (good), yellow (warning), red (critical) (FR-056). Tooltip with: title, analysis, references, suggested actions (FR-057). Dismissable (FR-059). |
| PMBlockInsightService | AI | Analyzes PM block data → generates insights. Sprint board: velocity trends, blocker detection. Dependency map: critical path risk. Capacity: overallocation warnings. Release notes: coverage gaps. |
| Insufficient data fallback | FE+AI | When <3 sprints of historical data → badge shows "Insufficient data — insights improve with more sprint history" (FR-058). Graceful degradation, no errors. |
| Insight refresh trigger | BE | Insights regenerated when: cycle data changes, issues added/removed, state transitions. Debounced: max 1 refresh per 30s per block. |

### Sprint 2 Gate

- [ ] Sprint board renders 6 lanes with correct issues (integration test)
- [ ] Drag-drop transitions call existing state API (E2E test)
- [ ] AI state transition proposal with [Approve] [Reject] (integration test)
- [ ] Sprint board read-only when CRDT unavailable (unit test)
- [ ] Dependency map renders DAG with critical path (integration test)
- [ ] DAG renders <1s for 50 nodes (performance test, FR-129)
- [ ] Circular dependency detected and displayed (unit test)
- [ ] Capacity plan shows correct utilization (integration test)
- [ ] Release notes auto-generated with correct classification (integration test)
- [ ] Human edits preserved during regeneration (unit test)
- [ ] Insight badges appear <3s with correct severity (integration test)
- [ ] Insufficient data shows graceful fallback (unit test)
- [ ] Contract test: backend PM types == frontend PM types (CI test)
- [ ] `estimate_hours` and `weekly_available_hours` columns work (migration test)
- [ ] Test coverage >80% for new code

---

## Cross-Sprint Concerns

### Migration Strategy

| Migration | Sprint | Contents |
|-----------|--------|----------|
| 042 | Sprint 1 | `note_versions` table + RLS + indexes + auto-version pg_cron function |
| 043 | Sprint 2 | `pm_block_insights` table + `issues.estimate_hours` column + `workspace_members.weekly_available_hours` column |

### Risk Mitigations

| Risk | Mitigation | Sprint |
|------|-----------|--------|
| R-008: Version storage grows rapidly | Retention policy (count + age), pinned exemptions, delta storage consideration | Sprint 1 |
| R-010: Dependency map layout slow | Web worker for layout >50 nodes, dagre for efficient DAG layout | Sprint 2 |
| R-011: AI insight predictions inaccurate | Confidence levels, 3-sprint minimum, dismissable badges | Sprint 2 |
| R-012: Release notes classification <80% | Confidence scores, manual override, "Uncategorized" fallback | Sprint 2 |

### Testing Strategy

- **Unit tests**: Domain entities, services, TipTap extensions, components. >80% coverage per sprint.
- **Integration tests**: Version CRUD with RLS, diff computation, restore flow, PM block data APIs, insight generation.
- **Performance tests**: AI digest <3s, DAG render <1s at 50 nodes, insight badges <3s.
- **E2E tests**: Save version → diff → restore flow. Sprint board drag-drop → state change. Template workflow.
- **Contract tests**: PM block type list parity between backend and frontend (CI).
- **Migration tests**: New columns, table creation, pg_cron function.

---

## Dependencies

| External | Used By | Fallback |
|----------|---------|----------|
| Feature 016 M6a (CRDT) | Restore during collab (Yjs transaction) | Restore without CRDT: direct content replacement |
| Feature 016 M6b (Ownership) | PM block edit guards | PM blocks default to "shared" ownership |
| Anthropic Claude API (Sonnet) | AI digest, state transition proposals, release notes | Cached results, manual fallback |
| d3-dag or dagre | Dependency map layout | Fallback to simple list view |

---

## After Feature 017

1. **Delta storage**: Optimize version storage by storing diffs instead of full snapshots
2. **Version branching**: Fork a note from a historical version
3. **PM block analytics**: Cross-cycle trend analysis, team velocity charts
4. **Custom PM blocks**: User-defined block types with configurable fields

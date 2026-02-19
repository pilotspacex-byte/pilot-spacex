# Feature Specification: Note Versioning & PM Blocks

**Feature Number**: 017
**Branch**: `017-note-versioning-pm`
**Created**: 2026-02-18
**Updated**: 2026-02-19 (v1.1 — Applied CRITICAL decision C-9)
**Status**: Deferred (backlog from Feature 015 scope reduction)
**Author**: Tin Dang
**Depends on**: 016-note-collaboration (CRDT for version restore; Ownership for PM block edit guards)

---

## Overview

Point-in-time note snapshots with AI-powered change digest, plus 4 new PM block types for sprint ceremonies within notes.

| Module | Type | Summary |
|--------|------|---------|
| M6c — Version Engine | New | Auto/manual snapshots, diff, restore, AI digest |
| M6d — PM Block Engine | Extend | 4 new block types: sprint-board, dependency-map, capacity-plan, release-notes |

**Note**: The 6 existing PM block types (decision, form, raci, risk, timeline, dashboard) remain in production and are not affected by this spec.

---

## Module Interfaces

**M6c — Version Engine**:
```
snapshot(noteId, trigger:'auto'|'manual'|'ai_before'|'ai_after') → NoteVersion
diff(v1, v2) → DiffResult
restore(versionId) → NoteVersion
digest(versionId) → string
```

**M6d — PM Block Engine**:
```
render(type, data) → Component
getInsights(blockId) → PMBlockInsight[]
proposeTransition(issueId, newState) → ApprovalRequest
```

---

## Module Specifications

### M6c — Version Engine

**Functional Requirements** (FR-034–042):
- **FR-034**: Auto-version every 5 minutes of active editing.
- **FR-035**: Manual "Save Version" on demand.
- **FR-036**: Before/after versions for AI operations.
- **FR-037**: Per-intent execution versions with labels.
- **FR-038**: Preview, compare (visual diff), and restore.
- **FR-039**: Restore creates new version (non-destructive).
- **FR-040**: AI change digest within 3 seconds (cached).
- **FR-041**: Impact analysis listing affected entities.
- **FR-042**: Digest cache invalidated when linked entities change.

#### Restore Concurrency Safety (C-9)

Restore operations use optimistic locking to prevent concurrent restore conflicts.

- **FR-039-A** (C-9): Restore API MUST pass the `version_number` of the version being restored as a concurrency token.
- **FR-039-B** (C-9): Backend acquires a PostgreSQL advisory lock on `note_id` for the duration of the restore transaction. This prevents concurrent restores from interleaving.
- **FR-039-C** (C-9): If a concurrent restore is detected (another restore completed after the request was issued — detected via advisory lock contention or version_number mismatch), return `409 Conflict` with the competing version info.
- **FR-039-D** (C-9): On `409 Conflict`, frontend shows: "Another restore was applied. Reload to see current state." + [Reload] button. No auto-retry.
- **FR-039-E** (C-9): Non-CRDT fallback (if Feature 016 M6a was dropped): restore performs direct DB write to note content + triggers page refresh via SSE `note_restored` event.

**Retention** (FR-074–075):
- **FR-074**: Configurable retention (count + age).
- **FR-075**: Pinned versions exempt from cleanup.

---

### M6d — PM Block Engine

4 new PM block types for sprint ceremonies within notes.

**New Block Types** (FR-048–060):
- **FR-048**: Block types: sprint-board, dependency-map, capacity-plan, release-notes.
- **FR-049**: Sprint board: 6 state-based lanes.
- **FR-050**: AI-proposed state transitions with [Approve] [Reject].
- **FR-051**: Dependency map: DAG with critical path highlighting.
- **FR-052**: Zoom/pan for 20+ nodes.
- **FR-053**: Capacity plan: available vs committed hours per member.
- **FR-054**: Release notes: auto-generate from completed issues with AI classification.
- **FR-055**: Preserve human edits during regeneration.
- **FR-056**: AI insight badges (green/yellow/red) on PM blocks.
- **FR-057**: Badge tooltip with analysis, references, suggested actions.
- **FR-058**: Graceful degradation with "Insufficient data" when <3 sprints.
- **FR-059**: Dismissable insights.
- **FR-060**: Sprint board read-only fallback when CRDT unavailable.

**Data Extensions** (FR-061–062):
- **FR-061**: Issue: add `estimate_hours DECIMAL(6,1) NULL`.
- **FR-062**: WorkspaceMember: add `weekly_available_hours DECIMAL(5,1) DEFAULT 40`.

**Contract Safety** (FR-043–044):
- **FR-043**: Backend/frontend PM block type lists validated via automated test.
- **FR-044**: Test suite MUST fail on type divergence.

---

## Key Entities

| Entity | Module | Table | Purpose |
|--------|--------|-------|---------|
| NoteVersion | M6c | `note_versions` | Point-in-time note snapshots |
| PMBlockInsight | M6d | `pm_block_insights` | AI analysis for PM blocks |
| Issue (extended) | M6d | `issues` | Add `estimate_hours` column |
| WorkspaceMember (ext) | M6d | `workspace_members` | Add `weekly_available_hours` column |

---

## Edge Cases

### M6c — Version Engine
- Restore during collab → Creates new version, CRDT merges concurrent edits
- Concurrent restore detected → 409 Conflict response; frontend shows reload prompt (FR-039-C/D)
- Advisory lock timeout (>5s) → 503 Service Unavailable; retry safe (restore is idempotent per version_number)
- Non-CRDT restore fallback → Direct DB write + SSE `note_restored` event triggers page refresh (FR-039-E)
- AI digest timeout → "Summary unavailable" + Retry; diff view fallback
- Version with no linked entities → "No linked entities found" in impact section

### M6d — PM Block Engine
- Sprint board references deleted issues → Strikethrough "Issue deleted"
- Circular dependencies → Detect cycle, show warning, render non-cyclic subgraph
- No team members → Setup guidance linking to settings
- Classification confidence < 0.3 → "Uncategorized" with manual classify
- <3 sprints history → "Insufficient data" badge

---

## Success Criteria

| Module | Criteria | Target |
|--------|----------|--------|
| M6c Version | AI change digest generation | <3s for 95% |
| M6c Version | Impact analysis accuracy | >90% |
| M6d PM Blocks | Sprint ceremonies without external tools | 100% |
| M6d PM Blocks | DAG render for 50 nodes | <1 second |
| M6d PM Blocks | Insight badge appearance | <3 seconds |

---

## Risk Register

| ID | Risk | Score | Response |
|----|------|-------|----------|
| R-008 | Version storage grows rapidly | 9 | Retention policy, delta storage. |
| R-010 | Dependency map layout slow | 12 | Web worker, limit visible depth. |
| R-011 | AI insight predictions inaccurate | 9 | Confidence levels, 3-sprint minimum. |
| R-012 | Release notes classification < 80% | 9 | Confidence scores, manual override. |

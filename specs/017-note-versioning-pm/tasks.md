# Tasks: Note Versioning & PM Blocks (Feature 017)

**Spec**: v1.0 | **Plan**: v1.0 | **Generated**: 2026-02-19

---

## Legend

- **Status**: `[ ]` pending, `[~]` in progress, `[x]` done, `[-]` blocked
- **Layer**: DB (database/migration), BE (backend service), AI (agent/skill), FE (frontend), QA (test)
- **Deps**: Task IDs that must complete first

---

## Sprint 1: Version Engine (M6c)

### Phase 1a: Database + Domain

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-201 | [ ] Create migration 042: `note_versions` table | M6c | DB | Feature 016 complete | Table: UUID PK, note_id FK, workspace_id (RLS), trigger enum (auto/manual/ai_before/ai_after), content JSONB, label varchar(255) nullable, pinned boolean default false, digest text nullable, digest_cached_at timestamp nullable, created_by UUID FK, created_at. Index on (note_id, created_at DESC). RLS via workspace_id. |
| T-202 | [ ] Create migration 042: auto-version pg_cron function | M6c | DB | T-201 | SQL function `fn_auto_version_active_notes()`: finds notes with edits in last 5 min and no version in last 5 min → enqueues snapshot job. pg_cron schedules every 5 min. |
| T-203 | [ ] Create NoteVersion domain entity | M6c | BE | T-201 | Rich entity with: trigger validation (enum), label max 100 chars, immutable content after creation. Pinned flag. Digest cache check (stale if digest_cached_at < linked entity updated_at). |
| T-204 | [ ] Create NoteVersionRepository | M6c | BE | T-203 | Async CRUD + RLS. Queries: by note_id paginated (newest first), by trigger type, pinned only. Retention query: versions exceeding count/age limits (excluding pinned). Batch delete for retention cleanup. |
| T-205 | [ ] Unit tests for NoteVersion entity | M6c | QA | T-203 | Tests: entity creation, trigger validation, label length, immutability, pin/unpin, digest cache staleness. >80% coverage. |

### Phase 1b: Version Services

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-206 | [ ] Create VersionSnapshotService | M6c | BE | T-204 | `snapshot(noteId, trigger, label?, createdBy)` → loads current note content → creates NoteVersion. For ai_before/ai_after: callable from skill executor. Returns created version. |
| T-207 | [ ] Implement auto-version job handler | M6c | BE | T-206, T-202 | `AutoVersionJobHandler`: receives enqueued snapshot jobs from pg_cron. Calls VersionSnapshotService with trigger="auto". Runs via existing worker pattern. |
| T-208 | [ ] Create VersionDiffService | M6c | BE | T-204 | `diff(v1Id, v2Id)` → loads both versions → block-level diff: added (new block IDs), removed (missing block IDs), modified (same block ID, different content). Returns structured DiffResult with block-level changes. |
| T-209 | [ ] Create VersionRestoreService | M6c | BE | T-204, T-206 | `restore(versionId)` → creates new version (trigger="manual", label="Restored from {source}") → replaces current note content with version content. If CRDT active: apply as Yjs transaction to merge with concurrent edits. Non-destructive: original version preserved (FR-039). |
| T-210 | [ ] Create VersionDigestService | M6c | AI | T-204 | `digest(versionId)` → load version + previous version → compute diff → call Sonnet for human-readable summary. Cache in `note_versions.digest`. Invalidate when linked entities change (FR-042). <3s for 95% (FR-040). |
| T-211 | [ ] Create ImpactAnalysisService | M6c | AI | T-204 | `impact(versionId)` → scan version content for entity references (issue IDs like `[PS-42]`, note links). List affected entities with change type. Accuracy >90% (FR-041). |
| T-212 | [ ] Create RetentionService | M6c | BE | T-204 | `cleanup(noteId, maxCount?, maxAgeDays?)` → delete versions exceeding limits. Pinned versions exempt (FR-075). Defaults: 50 versions, 90 days. Configurable per workspace via settings. |
| T-213 | [ ] Wire ai_before/ai_after into skill executor | M6c | AI | T-206 | Before skill execution: call `snapshot(noteId, "ai_before")`. After: call `snapshot(noteId, "ai_after", label=skillName)`. Per-intent labels (FR-037). |
| T-214 | [ ] Create Version API router | M6c | BE | T-206, T-208, T-209, T-210, T-211, T-212 | Endpoints: `POST /api/v1/notes/{id}/versions` (manual), `GET .../versions` (paginated), `GET .../versions/{vId}`, `GET .../versions/{v1}/diff/{v2}`, `POST .../versions/{vId}/restore`, `GET .../versions/{vId}/digest`, `GET .../versions/{vId}/impact`, `PUT .../versions/{vId}/pin`, `DELETE .../versions/{vId}` (if not pinned). Pydantic v2 schemas. Auth required. |
| T-215 | [ ] Integration tests for version services | M6c | QA | T-214 | Tests: manual snapshot, auto-version trigger, ai_before/ai_after via skill, diff computation, restore non-destructive, digest generation, impact analysis, retention respects pinned. 10+ test cases. >80% coverage. |

### Phase 1c: Version UI

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-216 | [ ] Replace version history sidebar (full implementation) | M6c | FE | T-214 | Replace Feature 016 placeholder panel. Version list: trigger icon (auto/manual/AI), label, creator avatar, relative time, pinned badge. Infinite scroll via paginated API. Manual "Save Version" button at top with label input. |
| T-217 | [ ] Create visual diff view | M6c | FE | T-214, T-216 | Select two versions → show block-level diff. Added: green highlight. Removed: red strikethrough. Modified: yellow with inline changes. Side-by-side or inline toggle. |
| T-218 | [ ] Create restore confirmation dialog | M6c | FE | T-214, T-216 | Dialog: "Restore to version from {time}?". Shows mini-preview of target version. [Restore] button with loading state. Success toast with link to new version. If CRDT: warning that concurrent edits will be merged. |
| T-219 | [ ] Create version digest display | M6c | FE | T-214, T-216 | Each version entry: expandable AI digest (1-2 sentences). "Generating..." spinner if not cached. Impact analysis expandable below: list of affected entities with links. |
| T-220 | [ ] Create pin/unpin UI | M6c | FE | T-214, T-216 | Star icon on version entry. Pinned versions shown at top of list with "Pinned" badge. Tooltip: "Pinned versions are exempt from retention cleanup". Accessible: keyboard toggle, aria-pressed. |
| T-221 | [ ] Unit tests for version UI | M6c | QA | T-216, T-217, T-218, T-219, T-220 | Tests: version list renders, diff highlights correct blocks, restore dialog flow, digest lazy-loads, pin/unpin toggles. >80% coverage. Storybook stories. |
| T-222 | [ ] E2E test: version workflow | M6c | QA | T-221 | Flow: edit note → auto-version appears → manual "Save Version" → diff between two → restore old version → new version created → pin version. |

---

## Sprint 2: PM Block Engine (M6d)

### Phase 2a: Database + Infrastructure

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-223 | [ ] Create migration 043: `pm_block_insights` table | M6d | DB | Sprint 1 gate | Table: UUID PK, workspace_id (RLS), block_id varchar, block_type enum (sprint_board/dependency_map/capacity_plan/release_notes), insight_type varchar, severity enum (green/yellow/red), title varchar, analysis text, references JSONB, suggested_actions JSONB, confidence float(0-1), dismissed boolean default false, created_at, updated_at. Index on (block_id, dismissed). |
| T-224 | [ ] Create migration 043: add `estimate_hours` to issues | M6d | DB | T-223 | `ALTER TABLE issues ADD COLUMN estimate_hours DECIMAL(6,1) NULL` (FR-061). No backfill. |
| T-225 | [ ] Create migration 043: add `weekly_available_hours` to workspace_members | M6d | DB | T-223 | `ALTER TABLE workspace_members ADD COLUMN weekly_available_hours DECIMAL(5,1) DEFAULT 40` (FR-062). Backfill existing rows to 40. |
| T-226 | [ ] Create PMBlockInsight domain entity | M6d | BE | T-223 | Entity with: severity validation (green/yellow/red), confidence range (0-1), dismissal flag. References as typed list. |
| T-227 | [ ] Create PMBlockInsightRepository | M6d | BE | T-226 | CRUD + RLS. Queries: by block_id (non-dismissed), by workspace + block_type, by severity. Batch dismiss. |
| T-228 | [ ] Create PM block type contract test | M6d | QA | — | Automated test: set of PM block types in backend config == set in frontend config. Test MUST fail on divergence (FR-043, FR-044). Runs in CI. |
| T-229 | [ ] Unit tests for PMBlockInsight entity | M6d | QA | T-226 | Tests: creation, severity validation, confidence range, dismiss/undismiss. >80% coverage. |

### Phase 2b: Sprint Board Block

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-230 | [ ] Create SprintBoardBlock TipTap extension | M6d | FE | T-228 | New PM block type `sprint-board`. Renders 6 state-based lanes: Backlog, Todo, In Progress, In Review, Done, Cancelled (FR-049). Connected to cycle via `cycleId` block attribute. Fetches issues from board API. |
| T-231 | [ ] Create sprint board data API | M6d | BE | T-224 | `GET /api/v1/cycles/{id}/board` → issues grouped by state for cycle. Includes: issue title, assignee, estimate_hours, labels, priority. Paginated per lane (max 50 per lane). |
| T-232 | [ ] Implement sprint board drag-drop | M6d | FE | T-230 | Drag issue card between lanes → calls `PATCH /api/v1/issues/{id}/state`. Optimistic UI: move card immediately, rollback on API failure. Respect state machine constraints (e.g., can't drag to Backlog from Done without reopen). Toast on invalid transition. |
| T-233 | [ ] Implement AI state transition proposals | M6d | AI | T-230, T-227 | `proposeTransition(issueId, newState)` → LLM analyzes issue context → suggests state change with reasoning. Creates ApprovalRequest per DD-003. Rendered as [Approve] [Reject] overlay on issue card in sprint board (FR-050). |
| T-234 | [ ] Implement sprint board read-only fallback | M6d | FE | T-230 | When CRDT unavailable: sprint board renders read-only. No drag-drop. Message: "Collaborative editing required for drag-drop. Use issue detail page for state changes." (FR-060). |
| T-235 | [ ] Integration tests for sprint board | M6d | QA | T-231, T-232, T-233 | Tests: board renders with correct lanes, drag-drop transitions, invalid transition rejected, AI proposal with approve/reject, read-only fallback. |

### Phase 2c: Dependency Map Block

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-236 | [ ] Create DependencyMapBlock TipTap extension | M6d | FE | T-228 | New PM block type `dependency-map`. Renders DAG of issue dependencies for a project (FR-051). Block attribute: `projectId`. Fetches graph from API. |
| T-237 | [ ] Create dependency graph API | M6d | BE | — | `GET /api/v1/projects/{id}/dependency-graph` → nodes (issues with id, title, state, priority) + edges (issue_relations where type=BLOCKS). Includes critical path: longest path through graph calculated via topological sort + path length. |
| T-238 | [ ] Implement DAG rendering with zoom/pan | M6d | FE | T-236 | dagre layout engine for DAG positioning. Critical path highlighted (thicker edges, color). Zoom (scroll + pinch), pan (drag), fit-to-view button. Performant for 20+ nodes (FR-052). Web worker for layout at >50 nodes (R-010). <1s render for 50 nodes. |
| T-239 | [ ] Implement circular dependency detection | M6d | BE+FE | T-237 | Backend: detect cycles via DFS → return cycle info in API response. Frontend: show warning badge "Circular dependency detected". Render non-cyclic subgraph. List cyclic edges in tooltip. |
| T-240 | [ ] Integration tests for dependency map | M6d | QA | T-237, T-238, T-239 | Tests: DAG renders correctly, critical path highlighted, zoom/pan works, circular dependency warning shown, <1s at 50 nodes. |

### Phase 2d: Capacity Plan + Release Notes Blocks

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-241 | [ ] Create CapacityPlanBlock TipTap extension | M6d | FE | T-228, T-225 | New PM block type `capacity-plan`. Table: member name, available hours, committed hours, utilization %. Color: green <80%, yellow 80-100%, red >100% (FR-053). Block attribute: `cycleId`. |
| T-242 | [ ] Create capacity data API | M6d | BE | T-224, T-225 | `GET /api/v1/cycles/{id}/capacity` → per member: name, weekly_available_hours, sum of estimate_hours on assigned issues in cycle, utilization percentage. Handle: no estimate_hours → "Not estimated" marker. |
| T-243 | [ ] Create ReleaseNotesBlock TipTap extension | M6d | FE | T-228 | New PM block type `release-notes`. Displays auto-generated release notes grouped by category: Features, Bug Fixes, Improvements, Breaking Changes (FR-054). Editable sections. Regenerate button. |
| T-244 | [ ] Create release notes generation service | M6d | AI | T-243 | `generateReleaseNotes(cycleId)` → fetch completed issues → LLM classifies each by type (feature/bugfix/improvement/breaking) → generates markdown. Confidence <0.3 → "Uncategorized" (edge case). Preserve human edits: diff previous AI output vs current content, merge human changes (FR-055). |
| T-245 | [ ] Add estimate_hours to issue detail UI | M6d | FE | T-224 | Decimal input field on issue detail page. 0.5 increments. Nullable. Label: "Estimate (hours)". Validation: 0-9999.9. |
| T-246 | [ ] Add weekly_available_hours to member settings UI | M6d | FE | T-225 | Decimal input in workspace member settings. Default 40. Label: "Weekly Available Hours". Validation: 0-168. |
| T-247 | [ ] Integration tests for capacity + release notes | M6d | QA | T-242, T-244 | Tests: capacity shows correct utilization, no-estimate fallback, release notes generated with categories, human edits preserved on regenerate, uncategorized fallback. |

### Phase 2e: AI Insight Badges

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-248 | [ ] Create InsightBadge component | M6d | FE | T-227 | Badge overlay on PM blocks: green/yellow/red circle (FR-056). Tooltip: title, analysis text, references (links), suggested actions (FR-057). [Dismiss] button (FR-059). Accessible: aria-live for severity changes. |
| T-249 | [ ] Create PMBlockInsightService | M6d | AI | T-227 | Analyzes PM block data → generates insights per block type. Sprint board: velocity anomaly, blocker count, stale issues. Dependency map: critical path length, bottleneck nodes. Capacity: overallocation, underallocation. Release notes: coverage gaps. Stores in pm_block_insights. |
| T-250 | [ ] Implement insufficient data fallback | M6d | FE+AI | T-249 | When <3 completed sprints in workspace → insight badges show "Insufficient data" message (FR-058). No severity color. Tooltip: "Insights improve with more sprint history. Complete at least 3 sprints." |
| T-251 | [ ] Implement insight refresh trigger | M6d | BE | T-249 | Insights regenerated on: cycle data change, issue state transition, issue added/removed from cycle. Debounced: max 1 refresh per 30s per block_id. Enqueues to `ai_normal` queue. |
| T-252 | [ ] Integration tests for insight badges | M6d | QA | T-248, T-249, T-250, T-251 | Tests: badge renders with correct severity, tooltip content, dismiss works, insufficient data fallback, refresh triggers on data change, debounce prevents excessive refreshes. >80% coverage. |

### Phase 2f: Final Integration

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-253 | [ ] E2E test: sprint board workflow | M6d | QA | T-235 | Flow: open note → insert sprint-board block → issues appear in lanes → drag issue → state changes → AI proposes transition → approve. |
| T-254 | [ ] E2E test: dependency + capacity workflow | M6d | QA | T-240, T-247 | Flow: insert dependency-map → view DAG → check critical path → insert capacity-plan → view utilization → set estimate on issue → utilization updates. |
| T-255 | [ ] E2E test: release notes workflow | M6d | QA | T-247 | Flow: complete sprint → insert release-notes block → auto-generate → edit a section → regenerate → human edits preserved. |
| T-256 | [ ] Performance test: DAG render at 50 nodes | M6d | QA | T-238 | Seed project with 50 issues + dependencies. Render dependency-map block. <1s total render time. 60fps interaction. |
| T-257 | [ ] Accessibility audit for PM blocks | M6d | QA | T-248 | Lighthouse accessibility >95 for all 4 new PM blocks. WCAG 2.2 AA. Focus management for drag-drop, tooltips, modals. Screen reader announces insight badges. |

---

## Summary

| Sprint | Tasks | New Tables | New Migrations | New Endpoints | Key Deliverables |
|--------|-------|------------|----------------|---------------|------------------|
| Sprint 1 | T-201 → T-222 (22) | note_versions | 042 | 9 (version CRUD + diff + restore + digest + impact + pin) | Version engine + diff + restore + AI digest |
| Sprint 2 | T-223 → T-257 (35) | pm_block_insights + 2 column additions | 043 | 4 (board + dependency graph + capacity + release notes gen) | 4 PM blocks + insight badges |
| **Total** | **57 tasks** | **2 new tables + 2 altered** | **2 migrations** | **13 new endpoints** | |

### Dependency Graph (Critical Path)

```
Sprint 1:
T-201 → T-202 (pg_cron)
T-201 → T-203 → T-204 → T-205
T-204 → T-206 → T-207 (auto-version worker)
T-204 → T-208 (diff)
T-204 + T-206 → T-209 (restore)
T-204 → T-210 (digest)
T-204 → T-211 (impact)
T-204 → T-212 (retention)
T-206 → T-213 (skill executor wire)
T-206 + T-208 + T-209 + T-210 + T-211 + T-212 → T-214 (API)
T-214 → T-215 (integration tests)
T-214 → T-216 → T-217, T-218, T-219, T-220 → T-221 → T-222

Sprint 2:
T-223 → T-224, T-225 → T-226 → T-227 → T-229
T-228 (contract test, parallel)
T-228 → T-230 → T-231, T-232, T-233, T-234 → T-235
T-228 → T-236 → T-237, T-238, T-239 → T-240
T-228 + T-225 → T-241 → T-242, T-245, T-246 → T-247
T-228 → T-243 → T-244 → T-247
T-227 → T-248 → T-249 → T-250, T-251 → T-252
T-235 → T-253
T-240 + T-247 → T-254
T-247 → T-255
T-238 → T-256
T-248 → T-257
```

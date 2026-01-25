# Task Detail Generation Plan

**Generated**: 2026-01-23
**Scope**: 28 missing sub-task details + 1 new phase file
**Mode**: `--incremental` (generate only missing tasks)

---

## Executive Summary

| Category | Count | Target Files |
|----------|-------|--------------|
| Missing Sub-Task Details | 28 | 7 existing files |
| New Phase File | 38 tasks | P9-Final-T323-T360.md |
| Header Updates | 7 | All affected files |
| **Total Changes** | **66 tasks** | **8 files** |

---

## Phase 1: Missing Sub-Task Details (28 tasks)

### Group A: P2 Foundational (5 tasks)

**File**: `P2-T024-T035.md` (1 task)

| Task ID | Description | Type | Complexity |
|---------|-------------|------|------------|
| T034a | Create Module SQLAlchemy model | IMPL | 🟢 5/20 |

**File**: `P2-T036-T050.md` (2 tasks)

| Task ID | Description | Type | Complexity |
|---------|-------------|------|------------|
| T040a | Create AIConfiguration model | IMPL | 🟡 6/20 |
| T048a | Create rate limiting middleware | IMPL | 🟡 7/20 |

**File**: `P2-T051-T067.md` (2 tasks)

| Task ID | Description | Type | Complexity |
|---------|-------------|------|------------|
| T053a | Create AIConfiguration schemas/endpoints | IMPL | 🟡 6/20 |
| T066a | Create Edge Function timeout handler | IMPL | 🟡 6/20 |

---

### Group B: P3-US01 Backend (7 tasks)

**File**: `P3-US01-T068-T096.md`

| Task ID | Description | Type | Complexity |
|---------|-------------|------|------------|
| T073a | Create NoteIssueLink junction table | IMPL | 🟢 4/20 |
| T091a | Create AI error types | IMPL | 🟢 4/20 |
| T091b | Implement circuit breaker pattern | IMPL | 🟡 7/20 |
| T091c | Create retry decorator | IMPL | 🟢 5/20 |
| T091d | Implement graceful degradation | IMPL | 🟡 6/20 |
| T091e | Create AI telemetry middleware | IMPL | 🟡 6/20 |
| T091f | Create ConversationAgent | IMPL | 🟡 8/20 |

---

### Group C: P3-US01 Frontend (4 tasks)

**File**: `P3-US01-T097-T117.md`

| Task ID | Description | Type | Complexity |
|---------|-------------|------|------------|
| T110a | Create VersionHistoryPanel component | IMPL | 🟡 6/20 |
| T112a | Add `is_pinned` field to Note model | IMPL | 🟢 4/20 |
| T112b | Add pin/unpin endpoint | IMPL | 🟢 4/20 |
| T112c | Create PinnedNotesList component | IMPL | 🟢 5/20 |

---

### Group D: P4-US02 Full Stack (10 tasks)

**File**: `P4-US02-T118-T154.md`

| Task ID | Description | Type | Complexity |
|---------|-------------|------|------------|
| T129a | Create ApprovalFlowService | IMPL | 🟡 7/20 |
| T129b | Create activity logging decorator | IMPL | 🟢 5/20 |
| T129c | Integrate activity logging into Issue services | IMPL | 🟢 4/20 |
| T129d | Integrate activity logging into Note services | IMPL | 🟢 4/20 |
| T150a | Create IssueFilter component | IMPL | 🟡 6/20 |
| T150b | Create IssueCalendarView component | IMPL | 🟡 7/20 |
| T154a | Add restore endpoint | IMPL | 🟢 4/20 |
| T154b | Add trash view endpoint | IMPL | 🟢 4/20 |
| T154c | Create TrashView component | IMPL | 🟢 5/20 |
| T154d | Add RLS policy for restore | IMPL | 🟢 4/20 |

---

### Group E: P6-US18 GitHub (3 tasks)

**File**: `P6-US18-T172-T192.md`

| Task ID | Description | Type | Complexity |
|---------|-------------|------|------------|
| T184a | Create scheduled commit scanner job | IMPL | 🟡 6/20 |
| T189a | Create branch name generation endpoint | IMPL | 🟢 4/20 |
| T189b | Add copy-to-clipboard to BranchSuggestion | IMPL | 🟢 3/20 |

---

### Group F: P7-US03 PR Review (1 task)

**File**: `P7-US03-T193-T200.md`

| Task ID | Description | Type | Complexity |
|---------|-------------|------|------------|
| T195a | Register PR review handler with Supabase Queues | IMPL | 🟢 4/20 |

---

## Phase 2: New Polish Phase File (38 tasks)

**New File**: `P9-Final-T323-T360.md`

### Testing (T323-T329d) - 11 tasks

| Task ID | Description | Type | Complexity |
|---------|-------------|------|------------|
| T323 | Create backend test configuration | SETUP | 🟢 5/20 |
| T324 | Create integration tests for auth | TEST | 🟡 6/20 |
| T325 | Create integration tests for notes | TEST | 🟡 7/20 |
| T326 | Create integration tests for issues | TEST | 🟡 7/20 |
| T327 | Create frontend component tests for NoteCanvas | TEST | 🟡 8/20 |
| T328 | Create E2E tests for note workflow | TEST | 🟡 8/20 |
| T329 | Create E2E tests for issue workflow | TEST | 🟡 8/20 |
| T329a | Create E2E tests for PR review workflow | TEST | 🟡 7/20 |
| T329b | Create E2E tests for cycle/sprint workflow | TEST | 🟡 7/20 |
| T329c | Create E2E tests for AI context workflow | TEST | 🟡 7/20 |
| T329d | Create E2E tests for GitHub integration | TEST | 🟡 7/20 |

### Documentation (T330-T332) - 3 tasks

| Task ID | Description | Type | Complexity |
|---------|-------------|------|------------|
| T330 | Update API documentation with OpenAPI | IMPL | 🟡 6/20 |
| T331 | Create developer setup guide | IMPL | 🟢 5/20 |
| T332 | Validate quickstart.md | TEST | 🟢 4/20 |

### Performance (T333-T335) - 3 tasks

| Task ID | Description | Type | Complexity |
|---------|-------------|------|------------|
| T333 | Optimize note canvas for 1000+ blocks | IMPL | 🟠 12/20 |
| T334 | Add Redis caching for AI responses | IMPL | 🟡 7/20 |
| T335 | Add database query optimization | REFACTOR | 🟡 8/20 |

### Security (T336-T337) - 2 tasks

| Task ID | Description | Type | Complexity |
|---------|-------------|------|------------|
| T336 | Audit RLS policies | TEST | 🟡 7/20 |
| T337 | Audit rate limiting configuration | TEST | 🟢 5/20 |

### Infrastructure (T338-T343) - 6 tasks

| Task ID | Description | Type | Complexity |
|---------|-------------|------|------------|
| T338 | Create Kubernetes manifests | SETUP | 🟡 8/20 |
| T339 | Create Terraform modules | SETUP | 🟡 8/20 |
| T340 | Configure health check endpoints | IMPL | 🟢 5/20 |
| T341 | Create environment configuration templates | SETUP | 🟢 5/20 |
| T342 | Create backup script | IMPL | 🟢 5/20 |
| T343 | Document failover procedure | IMPL | 🟢 4/20 |

### Accessibility (T344-T346) - 3 tasks

| Task ID | Description | Type | Complexity |
|---------|-------------|------|------------|
| T344 | Add axe-core accessibility tests | TEST | 🟡 6/20 |
| T345 | Create keyboard navigation tests | TEST | 🟡 6/20 |
| T346 | Add screen reader ARIA audit checklist | IMPL | 🟢 5/20 |

### Human-in-the-Loop (T354-T356) - 3 tasks

| Task ID | Description | Type | Complexity |
|---------|-------------|------|------------|
| T354 | Create ApprovalDialog component | IMPL | 🟡 7/20 |
| T355 | Create useApprovalFlow hook | IMPL | 🟡 6/20 |
| T356 | Add approval integration to modals | IMPL | 🟡 7/20 |

### Data Export/Import (T357-T360) - 4 tasks

| Task ID | Description | Type | Complexity |
|---------|-------------|------|------------|
| T357 | Create JSON schema definitions | IMPL | 🟡 6/20 |
| T358 | Create ExportWorkspaceService | IMPL | 🟡 8/20 |
| T359 | Create ImportWorkspaceService | IMPL | 🟡 9/20 |
| T360 | Add export/import endpoints | IMPL | 🟡 6/20 |

---

## Phase 3: Header Updates (7 files)

| File | Current | Updated | Change |
|------|---------|---------|--------|
| `P2-T024-T035.md` | 12 tasks | 13 tasks | +1 |
| `P2-T036-T050.md` | 15 tasks | 17 tasks | +2 |
| `P2-T051-T067.md` | 17 tasks | 19 tasks | +2 |
| `P3-US01-T068-T096.md` | 29 tasks | 36 tasks | +7 |
| `P3-US01-T097-T117.md` | 22 tasks | 26 tasks | +4 |
| `P4-US02-T118-T154.md` | 42 tasks | 52 tasks | +10 |
| `P6-US18-T172-T192.md` | 21 tasks | 24 tasks | +3 |
| `P7-US03-T193-T200.md` | 13 tasks | 14 tasks | +1 |

---

## Execution Order

### Step 1: Generate P2 Sub-Tasks (5 tasks)
```bash
# Files: P2-T024-T035.md, P2-T036-T050.md, P2-T051-T067.md
# Tasks: T034a, T040a, T048a, T053a, T066a
```

### Step 2: Generate P3-US01 Backend Sub-Tasks (7 tasks)
```bash
# File: P3-US01-T068-T096.md
# Tasks: T073a, T091a-f
```

### Step 3: Generate P3-US01 Frontend Sub-Tasks (4 tasks)
```bash
# File: P3-US01-T097-T117.md
# Tasks: T110a, T112a-c
```

### Step 4: Generate P4-US02 Sub-Tasks (10 tasks)
```bash
# File: P4-US02-T118-T154.md
# Tasks: T129a-d, T150a-b, T154a-d
```

### Step 5: Generate P6-US18 Sub-Tasks (3 tasks)
```bash
# File: P6-US18-T172-T192.md
# Tasks: T184a, T189a-b
```

### Step 6: Generate P7-US03 Sub-Task (1 task)
```bash
# File: P7-US03-T193-T200.md
# Task: T195a
```

### Step 7: Create P9-Final-T323-T360.md (38 tasks)
```bash
# New file with all Polish phase tasks
```

### Step 8: Update Headers and _INDEX.md
```bash
# Update task counts in all affected files
# Regenerate _INDEX.md with new totals
```

---

## Validation Checklist

After generation:

- [ ] All 28 sub-tasks have detail sections in their files
- [ ] P9-Final-T323-T360.md exists with 38 task details
- [ ] All file headers show correct task counts
- [ ] _INDEX.md reflects updated totals (361 → 399 tasks with details)
- [ ] No duplicate task IDs
- [ ] All task dependencies valid
- [ ] Mermaid graph renders correctly

---

## Dev Patterns to Load

| Pattern | File | Purpose |
|---------|------|---------|
| Pilot Space | `docs/dev-pattern/45-pilot-space-patterns.md` | Project overrides |
| Service Layer | `docs/dev-pattern/08-service-layer-pattern.md` | CQRS-lite |
| Repository | `docs/dev-pattern/07-repository-pattern.md` | Data access |
| Testing | `docs/dev-pattern/03-testing-standards.md` | Test patterns |
| Component | `docs/dev-pattern/20-frontend-component-patterns.md` | UI components |
| MobX State | `docs/dev-pattern/21c-frontend-mobx-state.md` | State management |

---

## Next Steps

After plan approval:
1. Execute `/speckit.tasks-detail --incremental` to generate missing tasks
2. Run `/speckit.analyze` to verify consistency
3. Commit changes with message: `feat(specs): Add 66 task details for MVP completeness`

---
description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Source**: `/specs/[###-feature-name]/`
**Required**: plan.md, spec.md
**Optional**: research.md, data-model.md, contracts/, quickstart.md

---

## Task Format

```
- [ ] [ID] [P?] [Story?] Description with exact file path
```

| Marker | Meaning |
|--------|---------|
| `[P]` | Parallelizable (different files, no dependencies) |
| `[USn]` | User story label (Phase 3+ only) |

**Examples**:
```
- [ ] T001 Create project structure per implementation plan
- [ ] T005 [P] Implement auth middleware in src/middleware/auth.py
- [ ] T012 [P] [US1] Create User model in src/models/user.py
```

---

## Phase 1: Setup

Project initialization and shared infrastructure.

- [ ] T001 Create project structure per plan.md
- [ ] T002 Initialize project with framework dependencies
- [ ] T003 [P] Configure linting and formatting

---

## Phase 2: Foundational

Core infrastructure required before user story work.

- [ ] T004 Setup database schema and migrations
- [ ] T005 [P] Implement authentication framework
- [ ] T006 [P] Setup API routing and middleware
- [ ] T007 Create base models shared across stories
- [ ] T008 [P] Configure error handling and logging

**Checkpoint**: Foundation complete - user stories can start.

---

## Phase 3: User Story 1 - [Title] (P1) 🎯 MVP

**Goal**: [What this story delivers]
**Verify**: [How to test independently]

### Tests (if requested in spec)

Write tests first, verify they fail before implementation.

- [ ] T010 [P] [US1] Contract test in tests/contract/test_[name].py
- [ ] T011 [P] [US1] Integration test in tests/integration/test_[name].py

### Implementation

- [ ] T012 [P] [US1] Create [Entity] model in src/models/[entity].py
- [ ] T013 [US1] Implement [Service] in src/services/[service].py
- [ ] T014 [US1] Implement endpoint in src/api/[endpoint].py
- [ ] T015 [US1] Add validation and error handling

**Checkpoint**: US1 functional and testable independently.

---

## Phase N: Additional User Stories

Repeat Phase 3 pattern for each user story (US2, US3, etc.) in priority order.

Each story phase includes:
- Goal and independent verification
- Tests (if requested)
- Implementation tasks with file paths
- Checkpoint confirming independent testability

---

## Phase Final: Polish

Cross-cutting concerns after all stories complete.

- [ ] TXXX [P] Documentation updates
- [ ] TXXX Code cleanup and refactoring
- [ ] TXXX [P] Additional unit tests (if requested)
- [ ] TXXX Run quickstart.md validation

---

## Dependencies

### Phase Order

```
Setup → Foundational → User Stories (parallel or sequential) → Polish
```

### User Story Independence

- Each story can start after Foundational completes
- Stories can run in parallel (different developers) or sequentially (P1→P2→P3)
- Each story is independently testable

### Within Each Story

1. Tests (if included) - write first, verify failure
2. Models before services
3. Services before endpoints
4. Core before integration

### Parallel Opportunities

Tasks marked `[P]` in the same phase can run concurrently:

```bash
# Example: Launch US1 models in parallel
Task: "Create User model in src/models/user.py"
Task: "Create Profile model in src/models/profile.py"
```

---

## Implementation Strategy

### MVP First

1. Setup → Foundational → US1 only
2. Validate US1 works independently
3. Deploy/demo if ready

### Incremental

1. Complete Foundation
2. Add US1 → test → deploy
3. Add US2 → test → deploy
4. Continue per priority

---

## Notes

- Tests optional: include only if spec.md requests them or user specifies TDD
- Paths shown assume single project (`src/`, `tests/`) - adjust per plan.md
- Commit after each task or logical group

---

## AI Generation Hints

When generating tasks from this template:

### Task Quality

- Each task should be completable by an LLM without additional context
- Include exact file paths, not placeholders like `[file]`
- Use imperative verbs: "Create", "Implement", "Add", "Configure"
- One responsibility per task (avoid "Create X and implement Y")

### Dependency Detection

Mark task as **not** parallelizable when:
- It imports from another task's file
- It extends/inherits from another task's class
- It requires database tables from another task
- It calls functions defined in another task

### Story Mapping Rules

| Artifact | Assign To |
|----------|-----------|
| Entity used by one story | That story's phase |
| Entity used by multiple stories | Earliest story that needs it |
| Entity used by all stories | Phase 2 (Foundational) |
| Endpoint serving one story | That story's phase |
| Shared infrastructure | Phase 1 (Setup) or Phase 2 |

### File Path Inference

Derive paths from plan.md structure. Common patterns:
- Models: `src/models/{entity_snake_case}.py`
- Services: `src/services/{domain}_service.py`
- Endpoints: `src/api/v1/{domain}.py` or `src/routes/{domain}.py`
- Tests: Mirror src structure under `tests/`

### Validation Checklist

Before finalizing tasks.md:
- [ ] Every user story from spec.md has a corresponding phase
- [ ] Every entity from data-model.md has a creation task
- [ ] Every endpoint from contracts/ has an implementation task
- [ ] No circular dependencies between tasks
- [ ] Each story phase has a checkpoint statement
- [ ] Task IDs are sequential (T001, T002, ...)

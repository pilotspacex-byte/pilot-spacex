---
description: Generate an actionable, dependency-ordered tasks.md for the feature based on available design artifacts.
handoffs:
  - label: Analyze For Consistency
    agent: speckit.analyze
    prompt: Run a project analysis for consistency
    send: true
  - label: Implement Project
    agent: speckit.implement
    prompt: Start the implementation in phases
    send: true
---

## User Input

```text
$ARGUMENTS
```

Consider user input before proceeding (if not empty).
Load @docs/dev-pattern/README.md to understand project rules.

## Workflow

### 1. Setup

Run from repo root:
```bash
.specify/scripts/bash/check-prerequisites.sh --json
```

Parse `FEATURE_DIR` and `AVAILABLE_DOCS` from output. Use absolute paths throughout.

For arguments with single quotes (e.g., "I'm Groot"), use: `'I'\''m Groot'` or `"I'm Groot"`

### 2. Load Design Documents

Read from `FEATURE_DIR`:

| Document | Required | Contains |
|----------|----------|----------|
| plan.md | Yes | Tech stack, libraries, structure |
| spec.md | Yes | User stories with priorities (P1, P2, P3) |
| data-model.md | No | Entities to map to user stories |
| contracts/ | No | API endpoints to map to user stories |
| research.md | No | Decisions for setup tasks |
| quickstart.md | No | Test scenarios |

Generate tasks based on available documents only.

### 3. Generate Tasks

1. Extract tech stack and structure from plan.md
2. Extract prioritized user stories from spec.md
3. For each optional doc that exists:
   - data-model.md: Map entities to user stories
   - contracts/: Map endpoints to user stories
   - research.md: Extract decisions for setup tasks
4. Generate tasks organized by user story (see Task Format below)
5. Create dependency graph showing story completion order
6. Identify parallel execution opportunities per user story
7. Validate: each user story has complete tasks and is independently testable

### 4. Write tasks.md

Use `.specify/templates/tasks-template.md` as structure template.

**Required sections**:
- Feature name from plan.md
- Phase 1: Setup (project initialization)
- Phase 2: Foundational (blocking prerequisites for all user stories)
- Phase 3+: One phase per user story in priority order
- Final Phase: Polish & cross-cutting concerns

**Each user story phase includes**:
- Story goal and independent test criteria
- Tests (only if requested in spec)
- Implementation tasks with file paths

**Footer sections**:
- Dependencies showing story completion order
- Parallel execution examples
- Implementation strategy (MVP first)

### 5. Report

Output:
- Path to generated tasks.md
- Total task count and count per user story
- Parallel opportunities identified
- MVP scope suggestion (typically User Story 1)
- Format validation confirmation
- Suggest improvements if any issues found
- Generate task detail (/speckit.task-details)

Context: $ARGUMENTS

Each task should be specific enough for an LLM to complete without additional context.

---

## Task Format

### Checklist Syntax

```
- [ ] [TaskID] [P?] [Story?] Description with file path
```

| Component | Rule |
|-----------|------|
| Checkbox | Start with `- [ ]` |
| Task ID | Sequential: T001, T002, T003... |
| [P] marker | Include only if parallelizable (different files, no deps) |
| [Story] label | [US1], [US2], etc. for user story phases only; omit for Setup/Foundational/Polish |
| Description | Clear action with exact file path |

**Examples**:
```
- [ ] T001 Create project structure per implementation plan
- [ ] T005 [P] Implement auth middleware in src/middleware/auth.py
- [ ] T012 [P] [US1] Create User model in src/models/user.py
```

### Phase Structure

| Phase | Story Label | Purpose |
|-------|-------------|---------|
| 1: Setup | None | Project initialization |
| 2: Foundational | None | Blocking prerequisites for all stories |
| 3+: User Stories | [US1], [US2]... | One phase per story in priority order |
| Final: Polish | None | Cross-cutting concerns |

### Task Sources

| Source | Mapping |
|--------|---------|
| User stories (spec.md) | Each story → its own phase with models, services, endpoints |
| Contracts | Each endpoint → user story phase it serves |
| Data model | Each entity → earliest user story that needs it (or Setup if shared) |
| Infrastructure | Shared → Setup; Blocking → Foundational; Story-specific → story phase |

### Tests

Tests are optional. Include only if:
- Explicitly requested in spec.md
- User requests TDD approach in $ARGUMENTS

When included, write tests within each user story phase before implementation.

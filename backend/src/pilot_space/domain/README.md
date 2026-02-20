# Domain Layer - Pilot Space

**Parent**: `/backend/README.md`

---

## Overview

Core business logic and rules: rich domain entities, value objects, domain services (pure logic, no I/O), domain events, and business rule invariants.

All entity implementations live in `infrastructure/database/models/` (co-located with ORM) and are re-exported through `domain/models/`.

---

## Submodule Documentation

- **[models/README.md](models/README.md)** -- All 12 entity deep-dives: Issue (state machine, fields, relationships, indexes), Note (TipTap content), State (groups, defaults), Cycle (status lifecycle), Module, Activity (32 types), NoteAnnotation, NoteIssueLink, WorkspaceOnboarding

---

## Entity Quick Reference

| Entity | File | Purpose | Key Properties |
|--------|------|---------|----------------|
| Issue | `infrastructure/models/issue.py` | Work item with state machine | `identifier`, `is_completed`, `is_active`, `has_ai_enhancements` |
| Note | `infrastructure/models/note.py` | Collaborative document (Note-First home) | `calculate_reading_time()` |
| State | `infrastructure/models/state.py` | Workflow state (Backlog->Done) | `is_terminal`, `is_active` |
| Cycle | `infrastructure/models/cycle.py` | Sprint container | `is_active`, `is_completed` |
| Module | `infrastructure/models/module.py` | Epic/feature grouping | `is_active`, `is_complete` |
| Activity | `infrastructure/models/activity.py` | Audit trail (immutable, 32 types) | append-only |
| NoteAnnotation | `infrastructure/models/note_annotation.py` | AI margin suggestion | `confidence`, `status` |
| NoteIssueLink | `infrastructure/models/note_issue_link.py` | Note-Issue traceability | link_type |
| WorkspaceOnboarding | `onboarding.py` | 4-step onboarding state | `is_complete`, `completion_percentage` |

---

## Value Objects

| Value Object | Values |
|---|---|
| IssuePriority | NONE (default), LOW, MEDIUM, HIGH, URGENT |
| StateGroup | UNSTARTED, STARTED, COMPLETED, CANCELLED (terminal) |
| CycleStatus | DRAFT, PLANNED, ACTIVE, COMPLETED, CANCELLED |
| ModuleStatus | PLANNED, ACTIVE, COMPLETED, CANCELLED |
| AnnotationType | SUGGESTION, WARNING, QUESTION, INSIGHT, REFERENCE, ISSUE_CANDIDATE, INFO |
| AnnotationStatus | PENDING, ACCEPTED, REJECTED, DISMISSED |
| NoteLinkType | EXTRACTED, REFERENCED, RELATED, INLINE |

---

## Business Rules & Invariants

- **Issue State Machine**: Backlog -> Todo -> In Progress -> In Review -> Done. Done -> Todo (reopen). Any -> Cancelled. No skipping.
- **Cycle-State Constraints**: Backlog = no cycle. Todo = optional. In Progress/In Review = required active cycle. Done/Cancelled = cleared.
- **Sequence ID**: Auto-incremented per project (PS-1, PS-2). Race-safe via `max(sequence_id) + 1`.
- **AI Metadata**: Append-only (never deleted). Duplicate candidates + suggestions tracked with confidence scores.
- **Note Content**: Always valid TipTap/ProseMirror JSON: `{"type": "doc", "content": [...]}`
- **Workspace Scoping**: All multi-tenant entities require `workspace_id`. RLS enforced at DB level.

---

## Domain Services & Events

**Domain services**: Pure business logic with no I/O. Currently empty; services live in `application/services/`.

**Domain events**: Planned (IssueCreated, IssueStateChanged, etc.). Pattern: entities collect events in `.events` list, repositories publish after flush.

---

## Patterns

- **Rich Entities**: Embed behavior (state transitions, validation) in entity classes
- **Validation**: API boundary (Pydantic) -> Domain entity (business rules)
- **Immutable Value Objects**: Enums and OnboardingSteps are immutable
- **Aggregate Design**: Issue root + Activity + NoteIssueLink children

---

## File Organization

```
domain/
+-- onboarding.py               # WorkspaceOnboarding entity + OnboardingSteps
+-- models/
|   +-- __init__.py             # Re-exports from infrastructure
|   +-- README.md               # Entity deep-dives
+-- events/                     # Domain events (planned)
+-- services/                   # Domain services (planned)
```

---

## Related Documentation

- **Infrastructure models**: [infrastructure/database/README.md](../infrastructure/database/README.md)
- **Application services**: [application/README.md](../application/README.md)
- **Data model spec**: `specs/001-pilot-space-mvp/data-model.md`

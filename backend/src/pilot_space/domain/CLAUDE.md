# Domain Layer Documentation - Pilot Space

**Generated**: 2026-02-10
**Scope**: Complete domain layer analysis including rich entities, value objects, domain services, domain events, and business rules
**Language**: Python 3.12+

---

## Overview

The domain layer encapsulates Pilot Space's core business logic and rules. It contains:

- **Rich Domain Entities**: Issue, Note, Cycle, Module, Workspace, User, Project, State, Label, Activity
- **Value Objects**: IssuePriority, StateGroup, CycleStatus, ModuleStatus, AnnotationType, AnnotationStatus, NoteLinkType, ActivityType
- **Domain Services**: Pure business logic (no I/O) for complex operations
- **Domain Events**: DomainEvent base class for pub/sub communication
- **Business Rules & Invariants**: State machines, validation, constraints

All entities live in `/backend/src/pilot_space/domain/models/` with behaviors and validation in entity classes.

---

## Quick Reference

| Entity | File | Purpose | Key Methods |
|--------|------|---------|-------------|
| **Issue** | infrastructure/models/issue.py | Work item with state machine | `identifier`, `is_completed`, `is_active`, `has_ai_enhancements` |
| **Note** | infrastructure/models/note.py | Collaborative document (Note-First home) | `calculate_reading_time()` |
| **State** | infrastructure/models/state.py | Workflow state (Backlog→Done) | `is_terminal`, `is_active` |
| **Cycle** | infrastructure/models/cycle.py | Sprint/iteration container | `is_active`, `is_completed` |
| **Module** | infrastructure/models/module.py | Epic/feature grouping | `is_active`, `is_complete` |
| **Activity** | infrastructure/models/activity.py | Audit trail entry | (value object, no methods) |
| **Workspace** | infrastructure/models/workspace.py | Multi-tenant root container | (multi-tenant scoping) |
| **User** | infrastructure/models/user.py | Global user (synced Supabase Auth) | (no workspace scope) |
| **Project** | infrastructure/models/project.py | Issue/note container | (workspace-scoped) |
| **Label** | infrastructure/models/label.py | Issue categorization | (no behaviors) |
| **NoteAnnotation** | infrastructure/models/note_annotation.py | AI margin suggestion | `confidence`, `status` tracking |
| **NoteIssueLink** | infrastructure/models/note_issue_link.py | Note↔Issue relationship | (value object) |
| **WorkspaceOnboarding** | onboarding.py | 4-step onboarding state | State transitions, completion tracking |

---

## Rich Domain Entities

### Issue Entity

**File**: `/backend/src/pilot_space/infrastructure/database/models/issue.py`

Core work item for the platform. Issues are the primary business object with rich behavior and state machine.

**State Machine**:

```
Backlog → Todo → In Progress → In Review → Done
                                           ↓
                                      Cancelled (any ← Cancelled)
```

**Key Properties**: `identifier` (e.g., PS-123), `is_completed` (Done or Cancelled), `is_active` (In Progress or In Review), `has_ai_enhancements` (title/description/labels enhanced), `duplicate_candidates` (AI-detected from ai_metadata).

**Fields**:

| Field | Type | Constraint | Purpose |
|-------|------|-----------|---------|
| `sequence_id` | int | PK within project | Auto-incremented; never gaps |
| `name` | str(255) | NOT NULL | Issue title/summary |
| `description` | text | nullable | Detailed description (markdown) |
| `description_html` | text | nullable | Pre-rendered HTML |
| `priority` | enum | default=NONE | none/low/medium/high/urgent |
| `state_id` | UUID FK | NOT NULL | Current workflow state |
| `project_id` | UUID FK | NOT NULL | Parent project (cascade delete) |
| `assignee_id` | UUID FK | nullable | Assigned user (set null on delete) |
| `reporter_id` | UUID FK | NOT NULL | Creator (restrict on delete) |
| `cycle_id` | UUID FK | nullable | Sprint/iteration assignment |
| `module_id` | UUID FK | nullable | Epic/feature grouping |
| `parent_id` | UUID FK | nullable | For sub-task hierarchies |
| `estimate_points` | int | nullable | Story points estimate |
| `start_date` | date | nullable | Planned start date |
| `target_date` | date | nullable | Due date |
| `sort_order` | int | default=0 | Manual sort order |
| `ai_metadata` | JSONB | nullable | AI enhancements, duplicates, suggestions |

**AI Metadata Structure**: Tracks enhancements (title_enhanced, description_expanded), suggestions (labels_suggested with confidence scores), priority/assignee recommendations, duplicate candidates (with similarity scores and explanations), and metadata (model, timestamp).

**Relationships**:

- `project` (FK) - Parent project
- `state` (FK) - Current workflow state
- `assignee` (FK, nullable) - Assigned user
- `reporter` (FK) - Creator (not nullable)
- `cycle` (FK, nullable) - Sprint assignment
- `module` (FK, nullable) - Epic assignment
- `parent` (self-referential, nullable) - Parent issue
- `sub_issues` (reverse) - Child issues
- `labels` (many-to-many) - Categorization
- `activities` (one-to-many) - Audit trail
- `note_links` (one-to-many) - Note-First traceability
- `ai_context` (one-to-one, nullable) - Aggregated context

**Indexes** (13 total):

- `project_id`, `state_id`, `assignee_id`, `reporter_id`, `cycle_id`, `module_id`, `parent_id`
- `priority`, `is_deleted`, `created_at`, `target_date`
- Composite: `(project_id, state_id)`, `(project_id, assignee_id)`, `(workspace_id, project_id)`

**Constraints**:

- Unique: `(project_id, sequence_id)` - Sequence IDs don't gap within project
- All foreign keys non-nullable except optional assignments (assignee, cycle, module, parent)

---

### Note Entity

**File**: `/backend/src/pilot_space/infrastructure/database/models/note.py`

Primary document for Note-First workflow. Notes are collaborative canvases where thinking happens, and issues emerge naturally.

**Key Properties**: `calculate_reading_time()` (200 words/minute, minimum 1 minute).

**Fields**:

| Field | Type | Constraint | Purpose |
|-------|------|-----------|---------|
| `title` | str(500) | NOT NULL | Display title |
| `content` | JSONB | NOT NULL, default={} | TipTap/ProseMirror JSON doc |
| `summary` | text | nullable | AI-generated or user summary |
| `word_count` | int | default=0 | Computed word count |
| `reading_time_mins` | int | default=0 | Estimated reading time |
| `is_pinned` | bool | default=False | For quick access |
| `is_guided_template` | bool | default=False | Onboarding guided note flag |
| `template_id` | UUID FK | nullable | Base template used |
| `owner_id` | UUID FK | NOT NULL | Creator (cascade delete) |
| `project_id` | UUID FK | nullable | Project scope (optional) |
| `source_chat_session_id` | UUID FK | nullable | Homepage Hub origin |

**Content Structure** (TipTap JSON): `{"type": "doc", "content": [{block}, ...]}`

**Relationships**:

- `template` (FK, nullable) - Base template
- `owner` (FK) - Creator
- `project` (FK, nullable) - Project scope
- `source_chat_session` (FK, nullable) - Homepage origin
- `annotations` (one-to-many) - AI margin suggestions
- `discussions` (one-to-many) - Threaded discussions
- `issue_links` (one-to-many) - Note↔Issue traceability

**Indexes** (10 total):

- `project_id`, `owner_id`, `template_id`, `is_pinned`, `is_deleted`, `is_guided_template`, `created_at`, `source_chat_session_id`
- Full-text search: `to_tsvector('english', title)` with GIN

---

### State Entity (Workflow States)

**File**: `/backend/src/pilot_space/infrastructure/database/models/state.py`

Represents workflow states for issues. Can be workspace-wide (default) or project-specific.

**State Groups**: UNSTARTED (Backlog, Todo), STARTED (In Progress, In Review), COMPLETED (Done), CANCELLED.

**Default States** (created on workspace/project init):

| State | Group | Color | Sequence |
|-------|-------|-------|----------|
| Backlog | UNSTARTED | #94a3b8 | 0 |
| Todo | UNSTARTED | #60a5fa | 1 |
| In Progress | STARTED | #fbbf24 | 2 |
| In Review | STARTED | #a78bfa | 3 |
| Done | COMPLETED | #22c55e | 4 |
| Cancelled | CANCELLED | #ef4444 | 5 |

**Key Properties**: `is_terminal` (COMPLETED or CANCELLED), `is_active` (STARTED).

**Fields**:

| Field | Type | Constraint | Purpose |
|-------|------|-----------|---------|
| `name` | str(50) | NOT NULL | Display name |
| `color` | str(20) | default=#6b7280 | Hex color for UI |
| `group` | enum | NOT NULL | Categorization (unstarted/started/completed/cancelled) |
| `sequence` | int | default=0 | Display order (lower = earlier) |
| `project_id` | UUID FK | nullable | Project scope (NULL = workspace-wide) |

**Constraints**:

- Unique: `(workspace_id, project_id, name)` - State names unique per scope

---

### Cycle Entity (Sprints/Iterations)

**File**: `/backend/src/pilot_space/infrastructure/database/models/cycle.py`

Container for sprint/iteration tracking with velocity and burndown metrics.

**Status Lifecycle**:

```
draft → planned → active → completed
                            ↓
                        cancelled (from any)
```

**Key Properties**: `is_active` (ACTIVE status), `is_completed` (COMPLETED status).

**Fields**:

| Field | Type | Constraint | Purpose |
|-------|------|-----------|---------|
| `name` | str(255) | NOT NULL | Cycle name (e.g., "Sprint 1") |
| `description` | text | nullable | Optional context |
| `project_id` | UUID FK | NOT NULL | Parent project (cascade) |
| `status` | enum | default=DRAFT | Current status |
| `start_date` | date | nullable | Cycle start |
| `end_date` | date | nullable | Cycle end |
| `sequence` | int | default=0 | Display order |
| `owned_by_id` | UUID FK | nullable | Manager/scrum master |

**Relationships**:

- `project` (FK) - Parent project
- `owned_by` (FK, nullable) - Cycle manager
- `issues` (one-to-many) - Issues in this cycle

**Constraints**:

- Unique: `(project_id, name)` - Cycle names unique within project

**State Constraints** (Business Rules):

- Issues in Backlog: Cycle unassigned (no cycle)
- Issues in Todo: Cycle optional (backlog or sprint)
- Issues in In Progress: Cycle required (must be in active cycle)
- Issues in In Review: Cycle required (must remain in active cycle)
- Issues in Done: Cycle cleared when archived
- Issues in Cancelled: Cycle cleared immediately

---

### Module Entity (Epics/Features)

**File**: `/backend/src/pilot_space/infrastructure/database/models/module.py`

Epic/feature-level grouping for organizing related issues.

**Status Lifecycle**:

```
planned → active → completed
                       ↓
                   cancelled (from any)
```

**Key Properties**: `is_active` (ACTIVE status), `is_complete` (COMPLETED or CANCELLED).

**Fields**:

| Field | Type | Constraint | Purpose |
|-------|------|-----------|---------|
| `name` | str(255) | NOT NULL | Display name |
| `description` | text | nullable | Detailed description |
| `status` | enum | default=PLANNED | Lifecycle status |
| `target_date` | date | nullable | Deadline |
| `sort_order` | int | default=0 | Display order |
| `project_id` | UUID FK | NOT NULL | Parent project (cascade) |
| `lead_id` | UUID FK | nullable | Module lead/owner |

**Relationships**:

- `project` (FK) - Parent project
- `lead` (FK, nullable) - Module lead
- `issues` (one-to-many) - Issues in this module

**Constraints**:

- Unique: `(project_id, name)` - Module names unique within project

---

### Activity Entity (Audit Trail)

**File**: `/backend/src/pilot_space/infrastructure/database/models/activity.py`

Immutable record of all changes and actions on issues. Used for audit logging, activity timelines, and analytics.

**Activity Types** (32 total): Lifecycle (CREATED, UPDATED, DELETED, RESTORED), State/Priority (STATE_CHANGED, PRIORITY_CHANGED), Assignment (ASSIGNED, UNASSIGNED), Grouping (ADDED_TO_CYCLE, REMOVED_FROM_CYCLE, ADDED_TO_MODULE, REMOVED_FROM_MODULE), Labels (LABEL_ADDED, LABEL_REMOVED), Relationships (PARENT_SET, PARENT_REMOVED, SUB_ISSUE_ADDED, SUB_ISSUE_REMOVED), Dates (START_DATE_SET, TARGET_DATE_SET, ESTIMATE_SET), Notes (LINKED_TO_NOTE, UNLINKED_FROM_NOTE), Comments (COMMENT_ADDED, COMMENT_UPDATED, COMMENT_DELETED), AI (AI_ENHANCED, AI_SUGGESTION_ACCEPTED, AI_SUGGESTION_REJECTED, DUPLICATE_DETECTED, DUPLICATE_MARKED).

**Fields**:

| Field | Type | Constraint | Purpose |
|-------|------|-----------|---------|
| `issue_id` | UUID FK | NOT NULL | Target issue (cascade) |
| `actor_id` | UUID FK | nullable | User who performed action (NULL = system/AI) |
| `activity_type` | enum | NOT NULL | Type of activity |
| `field` | str(100) | nullable | Field name if update |
| `old_value` | text | nullable | Previous value |
| `new_value` | text | nullable | New value |
| `comment` | text | nullable | Comment text for comment activities |
| `metadata` | JSONB | nullable | Additional context |

**Immutability**:

- Activity records are never updated or deleted
- They are append-only (insert once, read many)
- `actor_id` can be NULL for system/AI actions
- Timestamps from `TimestampMixin` (created_at, updated_at = created_at for activities)

---

### NoteAnnotation Entity (AI Margin Suggestions)

**File**: `/backend/src/pilot_space/infrastructure/database/models/note_annotation.py`

AI-generated insights displayed in the right margin of notes. Supports human-in-the-loop workflow.

**Annotation Types**: SUGGESTION, WARNING, QUESTION, INSIGHT, REFERENCE, ISSUE_CANDIDATE, INFO.

**Annotation Status**: PENDING, ACCEPTED, REJECTED, DISMISSED.

**Fields**:

| Field | Type | Constraint | Purpose |
|-------|------|-----------|---------|
| `note_id` | UUID FK | NOT NULL | Parent note (cascade) |
| `block_id` | str(100) | NOT NULL | TipTap block ID |
| `type` | enum | default=SUGGESTION | Annotation type |
| `content` | text | NOT NULL | Annotation text |
| `confidence` | float | default=0.5 | AI confidence (0.0-1.0) |
| `status` | enum | default=PENDING | User processing status |
| `ai_metadata` | JSONB | nullable | Model, reasoning, context used |

**AI Metadata**: `model`, `type`, `reasoning`, `context_used`, `confidence_factors` (pattern_match, semantic_similarity).

---

### NoteIssueLink Entity (Note-First Traceability)

**File**: `/backend/src/pilot_space/infrastructure/database/models/note_issue_link.py`

Bidirectional links between notes and issues, supporting Note-First workflow traceability.

**Link Types**: EXTRACTED (issue created from note), REFERENCED (note references issue), RELATED (general relationship), INLINE (embedded in note).

**Fields**:

| Field | Type | Constraint | Purpose |
|-------|------|-----------|---------|
| `note_id` | UUID FK | NOT NULL | Source note (cascade) |
| `issue_id` | UUID FK | NOT NULL | Target issue (cascade) |
| `link_type` | enum | default=RELATED | Relationship type |
| `block_id` | str(100) | nullable | TipTap block where link originates |

**Constraints**:

- When issue is EXTRACTED from note: link_type = EXTRACTED, user approves creation
- When issue is REFERENCED in note: link_type = REFERENCED, bidirectional badge
- INLINE links: Issue rendered within note content at block_id location
- RELATED: General mention or loose relationship

---

### WorkspaceOnboarding Entity

**File**: `/backend/src/pilot_space/domain/onboarding.py`

Domain entity tracking 4-step onboarding progress. Uses value object pattern for steps.

**Onboarding Steps** (value object): `ai_providers`, `invite_members`, `first_note`, `role_setup`.

**Key Properties**: `completion_count` (0-4), `completion_percentage` (0-100), `is_complete` (all 4 steps).

**Key Methods**: `complete_step()`, `uncomplete_step()`, `dismiss()`, `reopen()`, `set_guided_note()`.

**Fields**:

| Field | Type | Constraint | Purpose |
|-------|------|-----------|---------|
| `workspace_id` | UUID FK | NOT NULL | Parent workspace |
| `steps` | Embedded | NOT NULL | OnboardingSteps value object |
| `guided_note_id` | UUID | nullable | ID of guided note |
| `dismissed_at` | datetime | nullable | Checklist dismissed timestamp |
| `completed_at` | datetime | nullable | All steps completed timestamp |

---

## Value Objects

Immutable enumerations defined by their attributes.

| Value Object | Values |
|---|---|
| **IssuePriority** | NONE (default), LOW, MEDIUM, HIGH, URGENT |
| **StateGroup** | UNSTARTED, STARTED, COMPLETED, CANCELLED (terminal) |
| **CycleStatus** | DRAFT, PLANNED, ACTIVE, COMPLETED, CANCELLED |
| **ModuleStatus** | PLANNED, ACTIVE, COMPLETED, CANCELLED |
| **AnnotationType** | SUGGESTION, WARNING, QUESTION, INSIGHT, REFERENCE, ISSUE_CANDIDATE, INFO |
| **AnnotationStatus** | PENDING, ACCEPTED, REJECTED, DISMISSED |
| **NoteLinkType** | EXTRACTED, REFERENCED, RELATED, INLINE |

---

## Domain Services

Domain services contain **pure business logic with no infrastructure dependencies**. Currently empty; services live in `/application/services/`.

Pure business logic services transform entities without I/O. Examples include state transition validation (sequence ordering, terminal state checks) and issue extraction from notes (title/description parsing, default state assignment).

---

## Domain Events

Domain events notify listeners of business-critical state changes. Emitted after successful persistence.

**Planned event types**: IssueCreated, IssueStateChanged, IssueAssigned, IssuePriorityChanged, NoteCreated, NoteAnnotationAdded, CycleStarted, CycleCompleted.

**Pattern**: Entities collect events in `.events` list. Repositories publish events after flush to get IDs. Event bus decouples listeners (e.g., Activity logging, Webhook notifications, Integration triggers).

---

## Business Rules & Invariants

**Issue State Machine**: Backlog → Todo → In Progress → In Review → Done. Done → Todo (reopen). Any → Cancelled. No state skipping. Terminal states (Done, Cancelled) cannot transition except reopen.

**Cycle-State Constraints**: Backlog issues have no cycle. Todo issues optional. In Progress/In Review issues must be in active cycle. Done/Cancelled issues cleared from cycle.

**Sequence ID**: Auto-incremented per project (PS-1, PS-2, etc.). Never gaps within project. Race condition prevention via `max(sequence_id) + 1` query.

**Priority**: Default NONE. Ordering by convention (NONE < LOW < MEDIUM < HIGH < URGENT), not enforced.

**AI Metadata**: Append-only (never deleted). Duplicate candidates, label suggestions, priority suggestions tracked with confidence scores.

**Note Content**: Always valid TipTap/ProseMirror JSON. `{"type": "doc", "content": [...]}`

**Annotation Confidence**: Float 0.0-1.0. Default 0.5 (neutral).

**Workspace Scoping**: All multi-tenant entities require `workspace_id`. RLS policies enforce at DB level. Always scope queries by workspace.

---

## Patterns & Conventions

**Rich Entities**: Embed behavior (state transitions, validation, AI metadata updates) in entity classes, not anemic data containers.

**Validation Layers**: API Boundary (Pydantic, shape/type coercion) → Domain Entity (business rules, invariants). Entities validate in constructors.

**Immutable Value Objects**: OnboardingSteps and enums (IssuePriority, StateGroup, etc.) are immutable. To update: create new instance or use `replace()`.

---

## Recommended Patterns for Domain Development

1. **Rich Entity Methods**: Add behavior for domain-specific operations (is_overdue, can_transition_to, mark_as_duplicate). Calculation-heavy methods belong in application services.

2. **Domain Services for Complex Rules**: Encapsulate multi-entity business rules (e.g., state transition validation considering both Issue and Cycle constraints).

3. **Aggregate Design**: Group related entities with clear boundaries (Issue Aggregate: Issue root + Activity children + NoteIssueLink children). Enforce consistency through root access only.

4. **Default Values**: Constructors provide sensible defaults (priority=NONE, state=Backlog, cycle=None for unstarted issues). Prevent half-initialized entities.

---

## Key Design Decisions (References)

| Decision | Rationale | Impact |
|----------|-----------|--------|
| **Rich entities** (DD-?) | Business logic closer to data | Easier testing, clearer intent |
| **State enum** (StateGroup) | Categorize states | Filtering, group by status |
| **AI metadata JSONB** (Issue) | Flexibility without schema changes | Easy additions, no migrations |
| **Activity append-only** | Audit trail integrity | Immutable history |
| **Workspace scoping** (RLS) | Multi-tenant security | Data isolation at DB level |
| **Sequence ID per project** | Human-readable identifiers | PS-1, PS-2, etc. |
| **Soft delete** (is_deleted) | Data recovery, audit trail | Logical deletion, not physical |

---

## Common Pitfalls & Solutions

| Pitfall | Problem | Solution |
|---------|---------|----------|
| N+1 queries | Accessing relationships without eager load | Use `.options(joinedload(...))` in repository |
| Missing workspace scope | Data leakage across workspaces | Always `.where(Issue.workspace_id == workspace_id)` + RLS |
| Mutating value objects | Breaking immutability (OnboardingSteps) | Create new instance: `replace(steps, field=value)` |
| Missing validation | Empty names, invalid states in DB | Validate in entity constructors, not just API boundary |
| Domain logic in services | Anemic entities, scattered rules | Move validation/transitions into entity methods |

---

## File Organization

```
backend/src/pilot_space/domain/
├── __init__.py                 # Domain layer exports
├── onboarding.py               # WorkspaceOnboarding entity + OnboardingSteps
├── models/
│   └── __init__.py             # Re-exports all domain models from infrastructure
├── events/
│   └── __init__.py             # Domain events (currently empty)
└── services/
    └── __init__.py             # Domain services (currently empty; logic in application/services)

# Actual implementations live in infrastructure for ORM integration
backend/src/pilot_space/infrastructure/database/models/
├── __init__.py
├── activity.py                 # Activity entity + ActivityType enum
├── cycle.py                    # Cycle entity + CycleStatus enum
├── issue.py                    # Issue entity + IssuePriority enum
├── label.py                    # Label entity
├── module.py                   # Module entity + ModuleStatus enum
├── note.py                     # Note entity
├── note_annotation.py          # NoteAnnotation + AnnotationType/Status enums
├── note_issue_link.py          # NoteIssueLink + NoteLinkType enum
├── project.py                  # Project entity
├── state.py                    # State entity + StateGroup enum
├── user.py                     # User entity (global, not workspace-scoped)
├── workspace.py                # Workspace entity
├── workspace_member.py         # WorkspaceMember + WorkspaceRole
└── ... (12 more models)
```

---

## Related Documentation

- **Backend Architecture**: `/backend/CLAUDE.md` (5-layer Clean Architecture overview)
- **Repository Pattern**: `/backend/src/pilot_space/infrastructure/database/repositories/` (BaseRepository[T])
- **Application Services**: `/backend/src/pilot_space/application/services/` (CQRS-lite execution)
- **Design Decisions**: `/docs/DESIGN_DECISIONS.md` (88 total decisions)
- **RLS Security**: `/docs/architect/rls-patterns.md` (multi-tenant isolation)

---

## Generation Metadata

**Scope**: 12 rich entities, 8 value objects, domain services, domain events, business rules.

**Patterns Detected**: Rich entities with behavior, state machines (Issue/Cycle/Module), value objects, append-only audit trail, soft delete, workspace scoping, AI metadata JSONB, relationships/aggregates.

**Coverage Gaps**: Domain services empty (logic in application/services), domain events structure defined but not implemented, no explicit value object classes (using enums).

**Suggested Next Steps**: Implement DomainEvent infrastructure, extract pure logic to domain services, add comprehensive entity validation, document state machine constraints, create duplicate detection service.

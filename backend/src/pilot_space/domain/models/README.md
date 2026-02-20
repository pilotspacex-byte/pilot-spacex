# Domain Models Deep-Dive - Pilot Space

**Parent**: [domain/README.md](../README.md)

---

## Overview

12 rich entities with behavior, validation, and business rules. Implementations in `infrastructure/database/models/`, re-exported through `domain/models/`. All multi-tenant entities require `workspace_id` with RLS enforcement.

---

## Issue Entity

**File**: `infrastructure/database/models/issue.py`

### State Machine

```
Backlog -> Todo -> In Progress -> In Review -> Done
                                               |
                                          Cancelled (any <- Cancelled)
```

Done -> Todo (reopen). No state skipping.

### Key Properties

`identifier` (e.g., PS-123), `is_completed`, `is_active`, `has_ai_enhancements`, `duplicate_candidates`

### Fields

| Field | Type | Constraint | Purpose |
|-------|------|-----------|---------|
| `sequence_id` | int | PK within project | Auto-incremented; never gaps |
| `name` | str(255) | NOT NULL | Issue title |
| `description` | text | nullable | Markdown description |
| `description_html` | text | nullable | Pre-rendered HTML |
| `priority` | enum | default=NONE | none/low/medium/high/urgent |
| `state_id` | UUID FK | NOT NULL | Current workflow state |
| `project_id` | UUID FK | NOT NULL | Parent project (cascade) |
| `assignee_id` | UUID FK | nullable | Assigned user |
| `reporter_id` | UUID FK | NOT NULL | Creator |
| `cycle_id` | UUID FK | nullable | Sprint assignment |
| `module_id` | UUID FK | nullable | Epic grouping |
| `parent_id` | UUID FK | nullable | Sub-task hierarchy |
| `estimate_points` | int | nullable | Story points |
| `start_date` / `target_date` | date | nullable | Planning dates |
| `sort_order` | int | default=0 | Manual ordering |
| `ai_metadata` | JSONB | nullable | AI enhancements, duplicates, suggestions |

### AI Metadata

Tracks: enhancements (title/description), suggestions (labels with confidence), priority/assignee recommendations, duplicate candidates (similarity scores).

### Relationships

project, state, assignee, reporter, cycle, module, parent, sub_issues, labels (M2M), activities (1:N), note_links (1:N), ai_context (1:1)

### Indexes (13)

Single: project_id, state_id, assignee_id, reporter_id, cycle_id, module_id, parent_id, priority, is_deleted, created_at, target_date. Composite: (project_id, state_id), (project_id, assignee_id), (workspace_id, project_id)

Unique: `(project_id, sequence_id)`

---

## Note Entity

**File**: `infrastructure/database/models/note.py`

Primary document for Note-First workflow. Method: `calculate_reading_time()` (200 wpm, min 1 min).

### Fields

| Field | Type | Constraint | Purpose |
|-------|------|-----------|---------|
| `title` | str(500) | NOT NULL | Display title |
| `content` | JSONB | NOT NULL, default={} | TipTap/ProseMirror JSON |
| `summary` | text | nullable | AI-generated summary |
| `word_count` | int | default=0 | Computed |
| `is_pinned` | bool | default=False | Quick access |
| `is_guided_template` | bool | default=False | Onboarding flag |
| `owner_id` | UUID FK | NOT NULL | Creator |
| `project_id` | UUID FK | nullable | Project scope |

Content structure: `{"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "..."}]}]}`

Relationships: template, owner, project, annotations (1:N), discussions (1:N), issue_links (1:N)

Indexes (10): project_id, owner_id, template_id, is_pinned, is_deleted, is_guided_template, created_at, source_chat_session_id + GIN full-text on title

---

## State Entity

**File**: `infrastructure/database/models/state.py`

Workflow states for issues. Workspace-wide (default) or project-specific.

### State Groups

| Group | States | Terminal |
|-------|--------|----------|
| UNSTARTED | Backlog, Todo | No |
| STARTED | In Progress, In Review | No |
| COMPLETED | Done | Yes |
| CANCELLED | Cancelled | Yes |

### Default States

Backlog (#94a3b8, seq 0), Todo (#60a5fa, 1), In Progress (#fbbf24, 2), In Review (#a78bfa, 3), Done (#22c55e, 4), Cancelled (#ef4444, 5)

Properties: `is_terminal`, `is_active`. Unique: `(workspace_id, project_id, name)`.

---

## Cycle Entity

**File**: `infrastructure/database/models/cycle.py`

### Status Lifecycle

```
draft -> planned -> active -> completed
                                |
                            cancelled (from any)
```

Fields: name (255), description, project_id (required), status (default DRAFT), start_date, end_date, sequence, owned_by_id. Unique: `(project_id, name)`.

### State-Cycle Constraints

| Issue State | Cycle Requirement |
|-------------|-------------------|
| Backlog | No cycle |
| Todo | Optional |
| In Progress / In Review | Required (active cycle) |
| Done / Cancelled | Cleared |

---

## Module Entity

**File**: `infrastructure/database/models/module.py`

Status lifecycle: `planned -> active -> completed` (cancelled from any). Properties: `is_active`, `is_complete`. Unique: `(project_id, name)`.

---

## Activity Entity

**File**: `infrastructure/database/models/activity.py`

Immutable audit trail. 32 activity types across categories: Lifecycle, State/Priority, Assignment, Grouping, Labels, Relationships, Dates, Notes, Comments, AI.

Fields: issue_id, actor_id (nullable = system/AI), activity_type, field, old_value, new_value, comment, metadata (JSONB). Never updated or deleted (append-only).

---

## NoteAnnotation Entity

**File**: `infrastructure/database/models/note_annotation.py`

AI-generated margin suggestions. Types: SUGGESTION, WARNING, QUESTION, INSIGHT, REFERENCE, ISSUE_CANDIDATE, INFO. Status: PENDING, ACCEPTED, REJECTED, DISMISSED.

Fields: note_id, block_id, type (default SUGGESTION), content, confidence (0.0-1.0, default 0.5), status (default PENDING), ai_metadata (JSONB: model, reasoning, context_used, confidence_factors).

---

## NoteIssueLink Entity

**File**: `infrastructure/database/models/note_issue_link.py`

Bidirectional Note-Issue links for Note-First traceability.

| Type | Description |
|------|-------------|
| EXTRACTED | Issue created from note |
| REFERENCED | Note references issue |
| RELATED | General mention |
| INLINE | Issue rendered within note at block_id |

Fields: note_id, issue_id, link_type (default RELATED), block_id (nullable).

---

## WorkspaceOnboarding Entity

**File**: `domain/onboarding.py`

4-step onboarding: ai_providers, invite_members, first_note, role_setup. Value object pattern for steps.

Properties: `completion_count`, `completion_percentage`, `is_complete`. Methods: `complete_step()`, `uncomplete_step()`, `dismiss()`, `reopen()`, `set_guided_note()`.

---

## Business Rules

| Rule | Details |
|------|---------|
| Issue State Machine | Backlog -> Todo -> In Progress -> In Review -> Done. Reopen: Done -> Todo. Any -> Cancelled. |
| Cycle-State | Backlog: no cycle. Todo: optional. In Progress/Review: required (active). Done/Cancelled: cleared. |
| Sequence ID | Per-project auto-increment. Race-safe: `max(sequence_id) + 1 FOR UPDATE`. |
| AI Metadata | Append-only. Tracked with confidence scores. |
| Note Content | Valid TipTap JSON: `{"type": "doc", "content": [...]}` |
| Workspace Scoping | All entities require workspace_id. RLS enforced at DB level. |

---

## Related Documentation

- **Domain layer**: [domain/README.md](../README.md)
- **Infrastructure models**: [infrastructure/database/README.md](../../infrastructure/database/README.md)
- **Application services**: [application/README.md](../../application/README.md)
- **Data model spec**: `specs/001-pilot-space-mvp/data-model.md`

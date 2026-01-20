# Issues (Work Items) Feature - Comprehensive Architecture Documentation

## Overview

The Issues (Work Items) feature in Plane is a comprehensive project management system that allows teams to create, organize, prioritize, and collaborate on work items. The system is built with a Django REST API backend and React/TypeScript frontend, implementing a sophisticated data model supporting sub-issues, relationships, comments, attachments, reactions, and activity tracking.

---

## Table of Contents

1. [Data Models](#data-models)
2. [API Endpoints](#api-endpoints)
3. [Business Logic & Workflows](#business-logic--workflows)
4. [Frontend Architecture](#frontend-architecture)
5. [Data Flow](#data-flow)
6. [Error Handling](#error-handling)
7. [Performance Considerations](#performance-considerations)
8. [Integration Patterns](#integration-patterns)

---

## Data Models

### Core Models

#### Issue Model
**File**: `apps/api/plane/db/models/issue.py`

The central model representing a work item/issue in the system.

| Field | Type | Purpose | Constraints |
|-------|------|---------|-------------|
| `id` | UUID | Primary identifier | Auto-generated |
| `name` | CharField(255) | Issue title/summary | Required |
| `description` | JSONField | Rich-text description (JSON format) | Optional |
| `description_html` | TextField | HTML version of description | Optional, default: `<p></p>` |
| `description_stripped` | TextField | Plain text (tags removed) | Optional, auto-generated |
| `description_binary` | BinaryField | Binary format for ProseMirror | Optional |
| `state` | ForeignKey(State) | Current workflow state | Auto-assigned to default state |
| `parent` | ForeignKey(Issue, self) | Parent issue for sub-issues | Optional, allows nesting |
| `priority` | CharField(choices) | Priority level | Choices: urgent, high, medium, low, none; default: none |
| `start_date` | DateField | Issue start date | Optional |
| `target_date` | DateField | Issue due date | Optional, must be >= start_date |
| `sequence_id` | IntegerField | Human-readable issue number | Auto-incremented per project, locked during creation |
| `estimate_point` | ForeignKey(EstimatePoint) | Story point estimate | Optional |
| `assignees` | ManyToMany(User) | Through `IssueAssignee` | Multiple assignees supported |
| `labels` | ManyToMany(Label) | Through `IssueLabel` | Multiple labels supported |
| `sort_order` | FloatField | Display order in list | Default: 65535, allows fractional ordering |
| `completed_at` | DateTimeField | Completion timestamp | Auto-set when state.group == "completed" |
| `archived_at` | DateField | Archive timestamp | Manual archival |
| `is_draft` | BooleanField | Draft status | Default: False, affects queryset filters |
| `type` | ForeignKey(IssueType) | Issue type classification | Optional, auto-assigned to default type |
| `external_source` | CharField(255) | Integration source (e.g., "github") | Optional, for external issue syncing |
| `external_id` | CharField(255) | External system ID | Optional, unique with external_source |

**Key Methods**:
- `save()`: Complex lifecycle management including state defaults, sequence ID allocation with advisory locks, sort order calculation, and HTML stripping

**Manager**: `IssueManager`
- Excludes triage states
- Excludes archived issues
- Excludes draft issues
- Excludes issues from archived projects

---

#### IssueAssignee Model

Join table for issue-to-user many-to-many relationship with audit tracking.

| Field | Type | Purpose |
|-------|------|---------|
| `issue` | ForeignKey(Issue) | Issue reference |
| `assignee` | ForeignKey(User) | Assigned user |
| `created_at`, `updated_at` | DateTime | Audit tracking |
| `created_by`, `updated_by` | ForeignKey(User) | Who made changes |

**Unique Constraint**: `(issue, assignee, deleted_at)` - soft-deleted records can be re-assigned

---

#### IssueComment Model

Comments on issues with full lifecycle management.

| Field | Type | Purpose | Details |
|-------|------|---------|---------|
| `issue` | ForeignKey(Issue) | Parent issue | CASCADE delete |
| `comment_stripped` | TextField | Plain text version | Auto-generated from HTML |
| `comment_html` | TextField | HTML version | Default: `<p></p>` |
| `comment_json` | JSONField | JSON format | For editor state |
| `description` | OneToOne(Description) | Linked description model | Created on save |
| `attachments` | ArrayField(URLField) | URL references | Max 10 URLs |
| `actor` | ForeignKey(User) | Comment author | Can be system (NULL allowed) |
| `access` | CharField | Access level | Choices: INTERNAL, EXTERNAL; default: INTERNAL |
| `edited_at` | DateTimeField | Edit timestamp | Optional |
| `parent` | ForeignKey(IssueComment, self) | Reply threading | Optional, allows comment nesting |

---

#### IssueActivity Model

Audit trail for all issue changes and events.

| Field | Type | Purpose |
|-------|------|---------|
| `issue` | ForeignKey(Issue) | Related issue (DO_NOTHING on delete) |
| `verb` | CharField | Action type (e.g., "created", "updated") |
| `field` | CharField | Changed field name |
| `old_value` | TextField | Previous value |
| `new_value` | TextField | New value |
| `comment` | TextField | Human-readable description |
| `attachments` | ArrayField(URLField) | Related file attachments |
| `actor` | ForeignKey(User) | User who made change |
| `issue_comment` | ForeignKey(IssueComment) | Linked comment (DO_NOTHING) |
| `old_identifier`, `new_identifier` | UUIDField | For parent/state/assignee changes |
| `epoch` | FloatField | Event timestamp (seconds) |

---

#### IssueRelation Model

Directed relationships between issues (blockers, duplicates, etc.).

| Field | Type | Purpose |
|-------|------|---------|
| `issue` | ForeignKey(Issue) | Source issue |
| `related_issue` | ForeignKey(Issue) | Target issue |
| `relation_type` | CharField | Relationship type |

**Relation Types**:

| Forward Type | Reverse Type | Semantics |
|--------------|--------------|-----------|
| `blocked_by` | `blocking` | "A is blocked by B" ↔ "B is blocking A" |
| `relates_to` | `relates_to` | Symmetric relationship |
| `duplicate` | `duplicate` | Symmetric - same issue |
| `start_before` | `start_after` | Sequential constraint |
| `finish_before` | `finish_after` | Sequential constraint |
| `implemented_by` | `implements` | Feature-to-PR relationship |

---

#### Supporting Models

- **IssueLink**: External URL references with metadata
- **IssueAttachment**: File attachments with S3 storage (5MB limit)
- **IssueReaction**: Emoji reactions on issues
- **CommentReaction**: Emoji reactions on comments
- **IssueSubscriber**: Notification subscriptions
- **IssueVote**: Upvoting/downvoting issues
- **IssueMention**: Tracks @mentions in descriptions/comments
- **IssueSequence**: Maintains sequential numbering for issue keys
- **IssueVersion**: Point-in-time snapshots of issue state
- **IssueDescriptionVersion**: Tracks description change history

---

## API Endpoints

### Work Item List & Creation

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/workspaces/{slug}/projects/{projectId}/issues/` | GET | List work items with pagination, filtering, ordering |
| `/api/workspaces/{slug}/projects/{projectId}/issues/` | POST | Create new work item |
| `/api/workspaces/{slug}/projects/{projectId}/issues/{issueId}/` | GET | Retrieve specific work item |
| `/api/workspaces/{slug}/projects/{projectId}/issues/{issueId}/` | PUT | Full replace of work item |
| `/api/workspaces/{slug}/projects/{projectId}/issues/{issueId}/` | PATCH | Partial update of work item |
| `/api/workspaces/{slug}/projects/{projectId}/issues/{issueId}/` | DELETE | Soft-delete work item |

### Comments

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/workspaces/{slug}/projects/{projectId}/issues/{issueId}/comments/` | GET | List comments |
| `/api/workspaces/{slug}/projects/{projectId}/issues/{issueId}/comments/` | POST | Create comment |
| `/api/workspaces/{slug}/projects/{projectId}/issues/{issueId}/comments/{commentId}/` | PATCH | Edit comment |
| `/api/workspaces/{slug}/projects/{projectId}/issues/{issueId}/comments/{commentId}/` | DELETE | Delete comment |

### Links & Attachments

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/workspaces/{slug}/projects/{projectId}/issues/{issueId}/issue-links/` | GET/POST | List/Add external links |
| `/api/assets/v2/workspaces/{slug}/projects/{projectId}/issues/{issueId}/attachments/` | GET/POST | List/Upload attachments |

### Bulk Operations

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/workspaces/{slug}/projects/{projectId}/bulk-operation-issues/` | POST | Bulk update properties |
| `/api/workspaces/{slug}/projects/{projectId}/bulk-delete-issues/` | DELETE | Bulk soft-delete |
| `/api/workspaces/{slug}/projects/{projectId}/bulk-archive-issues/` | POST | Bulk archive |

### Query Parameters

**Pagination & Ordering**:
- `cursor`: Pagination cursor for CursorPagination
- `per_page`: Items per page (default: 10)
- `order_by`: Sort field (supports: `-created_at`, `priority`, `state__name`, etc.)

**Filtering & Fields**:
- `fields`: Comma-separated fields to include in response
- `expand`: Related fields to expand (e.g., `assignees`, `labels`, `state`)

---

## Business Logic & Workflows

### Issue Lifecycle

```
Creation → Assignment → Work In Progress → Completion → Archival/Deletion
  ↓           ↓              ↓                 ↓            ↓
State: Backlog → Unstarted → Started → Completed → (Archived/Deleted)
```

### State Groups

| State Group | Purpose | Auto-Behavior |
|-------------|---------|---------------|
| `backlog` | Default initial state | - |
| `unstarted` | Planned but not started | - |
| `started` | In active work | - |
| `completed` | Finished work | `issue.completed_at` = current timestamp |
| `cancelled` | Abandoned/rejected | - |
| `triage` | New unreviewed issues | Excluded from normal queries |

### Sequence ID Generation

**Critical Locking Mechanism**:
```python
# Transaction-level advisory lock using project ID
lock_key = convert_uuid_to_integer(self.project.id)
with connection.cursor() as cursor:
    cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock_key])

# Atomic increment ensures no duplicates across concurrent requests
last_sequence = IssueSequence.objects.filter(project=self.project).aggregate(Max("sequence"))
self.sequence_id = last_sequence + 1
```

### Validation Rules

1. **Date Validation**: `start_date` cannot exceed `target_date`
2. **HTML Validation**: Parses, re-serializes, and sanitizes HTML
3. **Assignee Validation**: Assignees must be active project members with role >= 15
4. **Label Validation**: Labels must belong to same project
5. **State Validation**: State must belong to same project
6. **Parent Validation**: Parent issue must be in same project/workspace

### Activity Tracking

**Key Changes Tracked**:
- `name`: Issue title changes
- `description`: Description updates
- `state`: Status transitions
- `parent`: Sub-issue hierarchy changes
- `priority`: Priority updates
- `assignees`: Assignment changes
- `labels`: Label changes
- `start_date`, `target_date`: Date updates
- `estimate_point`: Estimation changes

---

## Frontend Architecture

### Service Layer

**File**: `apps/web/core/services/issue/issue.service.ts`

```typescript
class IssueService extends APIService {
  // Creation
  createIssue(slug, projectId, data): Promise<TIssue>

  // Retrieval
  getIssues(slug, projectId, queries): Promise<TIssuesResponse>
  retrieve(slug, projectId, issueId, queries): Promise<TIssue>

  // Updates
  patchIssue(slug, projectId, issueId, data): Promise<TIssue>

  // Deletion
  deleteIssue(slug, projectId, issueId): Promise<void>

  // Sub-issues
  subIssues(slug, projectId, issueId, queries): Promise<TIssueSubIssues>

  // Bulk Operations
  bulkOperations(slug, projectId, data): Promise<any>
  bulkDeleteIssues(slug, projectId, data): Promise<void>
}
```

### Store Layer (MobX)

**File**: `apps/web/core/store/issue/issue.store.ts`

```typescript
class IssueStore implements IIssueStore {
  // Observables
  issuesMap: Record<string, TIssue> = {}
  issuesIdentifierMap: Record<string, string> = {} // "PROJECT-123" → UUID

  // Actions
  addIssue(issues: TIssue[]): void
  updateIssue(issueId: string, issue: Partial<TIssue>): void
  removeIssue(issueId: string): void

  // Computed/Helper Methods
  getIssueById(issueId: string): TIssue | undefined
  getIssueIdByIdentifier(identifier: string): string | undefined
}
```

**Key Features**:
- Bidirectional mapping (ID ↔ Identifier)
- Optimistic updates with runInAction
- computedFn for memoized queries

### Type Definitions

**File**: `packages/types/src/issues/issue.ts`

```typescript
type TBaseIssue = {
  id: string
  sequence_id: number
  name: string
  sort_order: number
  state_id: string | null
  priority: TIssuePriorities | null
  label_ids: string[]
  assignee_ids: string[]
  sub_issues_count: number
  attachment_count: number
  link_count: number
  project_id: string | null
  parent_id: string | null
  cycle_id: string | null
  module_ids: string[] | null
  created_at: string
  updated_at: string
  start_date: string | null
  target_date: string | null
  completed_at: string | null
  archived_at: string | null
  is_draft: boolean
}
```

---

## Data Flow

### Issue Creation Flow

```
Frontend (User Action)
    ↓
IssueService.createIssue()
    ↓ POST /api/workspaces/{slug}/projects/{projectId}/issues/
    ↓
Backend: IssueListCreateAPIEndpoint.post()
    ↓
IssueSerializer.validate()
    ├─ Check external ID uniqueness
    ├─ Validate dates, HTML, assignees, labels, state
    └─ Return validated data
    ↓
IssueSerializer.create()
    ├─ Create Issue record with defaults
    ├─ Create IssueSequence for numbering
    ├─ Bulk-create IssueAssignee records
    └─ Bulk-create IssueLabel records
    ↓
async: issue_activity.delay()
    └─ Log IssueActivity record
    ↓
async: model_activity.delay()
    └─ Send webhook notification
    ↓
Return IssueSerializer(issue)
    ↓
Frontend: IssueStore.addIssue()
    ├─ Add to issuesMap[issueId]
    └─ Add to issuesIdentifierMap["PROJECT-123"]
    ↓
UI Update (MobX reaction)
```

### Issue Update Flow

```
Frontend (User edits issue)
    ↓
IssueService.patchIssue()
    ↓ PATCH /api/workspaces/{slug}/projects/{projectId}/issues/{issueId}/
    ↓
Backend: IssueDetailAPIEndpoint.patch()
    ↓
IssueSerializer.validate(partial_data)
    ↓
Update Issue model
    ├─ Apply field updates
    ├─ Trigger state logic if state changed
    └─ Update timestamps
    ↓
Handle many-to-many updates (if needed)
    ├─ assignees: Delete old → Create new IssueAssignee
    └─ labels: Delete old → Create new IssueLabel
    ↓
async: issue_activity.delay()
    └─ Track all field changes
    ↓
Frontend: IssueStore.updateIssue()
    ↓
UI Update (MobX reaction)
```

---

## Error Handling

### Validation Error Handling

```python
# Date validation
if start_date > target_date:
    raise serializers.ValidationError("Start date cannot exceed target date")

# HTML validation
try:
    parsed = html.fromstring(description_html)
    is_valid, error_msg, sanitized_html = validate_html_content(description_html)
    if not is_valid:
        raise serializers.ValidationError({"error": "html content is not valid"})
except Exception:
    raise serializers.ValidationError("Invalid HTML passed")
```

### External ID Conflict Handling

```python
if external_id and external_source:
    if Issue.objects.filter(...).exists():
        return Response(
            {
                "error": "Issue with same external id and source already exists",
                "id": str(issue.id)
            },
            status=status.HTTP_409_CONFLICT
        )
```

---

## Performance Considerations

### Database Query Optimization

```python
# Use select_related for ForeignKey fields
.select_related("project", "workspace", "state", "parent")

# Use prefetch_related for reverse ForeignKey and Many-to-Many
.prefetch_related("assignees", "labels")
```

### Concurrency Safety

1. **Advisory Locks for Sequence Generation**: PostgreSQL advisory locks prevent race conditions
2. **Unique Constraints with Soft Deletes**: Allows re-adding soft-deleted records

### Caching Strategy

**Frontend Caching**:
- **IssueStore**: In-memory MobX observables cache all loaded issues
- **Identifier Map**: Quick O(1) lookup from "PROJECT-123" → UUID
- **Computed Functions**: `computedFn` memoization for query results

### Async Processing

**Background Tasks** (via Celery):
- `issue_activity.delay()`: Don't wait for activity logging
- `model_activity.delay()`: Don't wait for webhooks

---

## Integration Patterns

### Activity Tracking System

```
Issue Updated
    ↓ (synchronous, in request)
Backend validates changes
    ↓ (asynchronous, background job)
issue_activity.delay() triggered
    ↓
Celery Task: Extract field changes
    ├─ Compare old vs new values
    ├─ Create IssueActivity records
    └─ Update IssueVersion/IssueDescriptionVersion
    ↓
Notification system:
    ├─ Query IssueSubscriber
    └─ Send notifications
```

### Webhook Events

**Triggered Events**:
- `issue.created`
- `issue.updated`
- `issue.deleted`
- `comment.created`
- `comment.updated`
- `comment.deleted`

---

## Key Architectural Decisions

1. **Soft Deletes Over Hard Deletes**: `deleted_at` timestamp field for audit trail
2. **Separate Description Model for Comments**: Decouples content versioning
3. **Advisory Locks for Sequence Generation**: Guarantees unique sequential IDs
4. **Async Activity Tracking**: Fast API responses, deferred logging
5. **ManyToMany Through Tables for Audit**: Full audit trail of changes

---

## File Reference Map

| Component | File Path |
|-----------|-----------|
| Core Models | `apps/api/plane/db/models/issue.py` |
| State Model | `apps/api/plane/db/models/state.py` |
| API Views | `apps/api/plane/api/views/issue.py` |
| Serializers | `apps/api/plane/api/serializers/issue.py` |
| Activity Task | `apps/api/plane/bgtasks/issue_activities_task.py` |
| IssueService | `apps/web/core/services/issue/issue.service.ts` |
| IssueStore | `apps/web/core/store/issue/issue.store.ts` |
| Type Definitions | `packages/types/src/issues/issue.ts` |

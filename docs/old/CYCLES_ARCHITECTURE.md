# Cycles (Sprints) Feature - Comprehensive Architecture Documentation

## Overview

The Cycles (Sprints) feature in Plane provides time-boxed iteration planning enabling sprint management with issue tracking, progress monitoring, and completion analytics. Cycles are project-scoped containers that group issues for a specific time period.

---

## Table of Contents

1. [Data Models](#data-models)
2. [API Endpoints](#api-endpoints)
3. [Business Logic](#business-logic)
4. [Frontend Architecture](#frontend-architecture)
5. [Data Flow](#data-flow)
6. [Error Handling](#error-handling)
7. [Performance Optimizations](#performance-optimizations)

---

## Data Models

### Core Cycle Model

**File**: `apps/api/plane/db/models/cycle.py`

```python
class Cycle(ProjectBaseModel):
    name = CharField(max_length=255)
    description = TextField()
    start_date = DateTimeField(null=True, blank=True)
    end_date = DateTimeField(null=True, blank=True)
    owned_by = ForeignKey(User)
    view_props = JSONField(default=dict)
    sort_order = FloatField(default=65535)
    logo_props = JSONField(default=dict)
    external_source = CharField(max_length=255, null=True)
    external_id = CharField(max_length=255, null=True)
    progress_snapshot = JSONField(default=dict)
    archived_at = DateTimeField(null=True)
    timezone = CharField(default="UTC")
    version = IntegerField(default=1)
```

**Key Features**:
- Cycles inherit from `ProjectBaseModel`, automatically inheriting `project` and `workspace` ForeignKey constraints
- `sort_order` uses float descending model: new cycles insert at (min_sort_order - 10000)
- `progress_snapshot` captures metrics at cycle completion for historical analysis
- `archived_at` implements soft-delete pattern (NULL = active, NOT NULL = archived)

### CycleIssue Junction Model

```python
class CycleIssue(ProjectBaseModel):
    issue = ForeignKey(Issue, on_delete=CASCADE, related_name="issue_cycle")
    cycle = ForeignKey(Cycle, on_delete=CASCADE, related_name="issue_cycle")

    class Meta:
        unique_together = ["issue", "cycle", "deleted_at"]
        constraints = [
            UniqueConstraint(
                fields=["cycle", "issue"],
                condition=Q(deleted_at__isnull=True),
                name="cycle_issue_when_deleted_at_null"
            )
        ]
```

### CycleUserProperties Model

```python
class CycleUserProperties(ProjectBaseModel):
    cycle = ForeignKey(Cycle, related_name="cycle_user_properties")
    user = ForeignKey(User)
    filters = JSONField(default=get_default_filters)
    display_filters = JSONField(default=get_default_display_filters)
    display_properties = JSONField(default=get_default_display_properties)
    rich_filters = JSONField(default=dict)
```

---

## API Endpoints

### Cycle CRUD Operations

**Base Path**: `/api/workspaces/{slug}/projects/{project_id}/cycles/`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/cycles/` | List all cycles with filtering |
| POST | `/cycles/` | Create new cycle |
| GET | `/cycles/{pk}/` | Get cycle details |
| PATCH | `/cycles/{pk}/` | Update cycle (with restrictions) |
| DELETE | `/cycles/{pk}/` | Delete cycle (admin/creator only) |

**Query Parameters (GET)**:
- `cycle_view`: "current" | "upcoming" | "completed" | "draft" | "incomplete" | "all"

**Status Filtering Logic**:
```
Current: start_date <= NOW <= end_date
Upcoming: start_date > NOW
Completed: end_date < NOW
Draft: start_date IS NULL AND end_date IS NULL
Incomplete: end_date >= NOW OR end_date IS NULL
```

### Cycle Issues (Work Items)

**Base Path**: `/api/workspaces/{slug}/projects/{project_id}/cycles/{cycle_id}/cycle-issues/`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/cycle-issues/` | List cycle's work items (paginated) |
| POST | `/cycle-issues/` | Assign multiple issues to cycle |
| GET | `/cycle-issues/{issue_id}/` | Get specific cycle-issue |
| DELETE | `/cycle-issues/{issue_id}/` | Remove issue from cycle |

**POST Request Body**:
```json
{
  "issues": ["uuid1", "uuid2", ...]
}
```

### Issue Transfer Between Cycles

**Endpoint**: `POST /api/workspaces/{slug}/projects/{project_id}/cycles/{cycle_id}/transfer-issues/`

**Request Body**:
```json
{
  "new_cycle_id": "target-cycle-uuid"
}
```

**Transfer Logic**:
1. Validate old_cycle has ended (end_date < NOW)
2. Validate new_cycle is not completed
3. Capture progress snapshot of old cycle
4. Transfer only incomplete issues (backlog, unstarted, started)
5. Persist snapshot to old_cycle.progress_snapshot

### Archive Operations

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/cycles/{cycle_id}/archive/` | Archive completed cycle |
| DELETE | `/cycles/{cycle_id}/archive/` | Unarchive cycle |
| GET | `/archived-cycles/` | List archived cycles |

---

## Business Logic

### Cycle Status Lifecycle

**Frontend Logic**:
```typescript
getStatus(): TCycleGroups {
  const endDate = getDate(c.end_date);
  const hasEndDatePassed = endDate && isPast(endDate);
  const isEndDateToday = endDate && isToday(endDate);

  if (hasEndDatePassed && !isEndDateToday) return "completed";
  if (isPast(startDate) && !isPast(endDate)) return "current";
  if (isFuture(startDate)) return "upcoming";
  if (!startDate && !endDate) return "draft";
}
```

### Progress Calculation

**Progress Snapshot Structure**:
```python
{
    "total_issues": int,
    "completed_issues": int,
    "cancelled_issues": int,
    "started_issues": int,
    "unstarted_issues": int,
    "backlog_issues": int,
    "distribution": {
        "labels": [...],
        "assignees": [...],
        "completion_chart": {...}
    },
    "estimate_distribution": {...}
}
```

### Update Restrictions

- Completed cycles (end_date < NOW) can ONLY have `sort_order` modified
- Archived cycles cannot be edited
- Both start_date and end_date must either be provided together or both NULL

### Validation Rules

```python
# POST/PATCH require:
(start_date IS NULL AND end_date IS NULL)
  OR
(start_date IS NOT NULL AND end_date IS NOT NULL)

# AND if both set:
start_date <= end_date
```

---

## Frontend Architecture

### MobX Store (CycleStore)

**File**: `apps/web/core/store/cycle.store.ts`

**Observable State**:
```typescript
cycleMap: Record<string, ICycle>
plotType: Record<string, TCyclePlotType>
estimatedType: Record<string, TCycleEstimateType>
activeCycleIdMap: Record<string, boolean>
fetchedMap: Record<string, boolean>
loader: boolean
progressLoader: boolean
```

**Computed Properties**:
```typescript
currentProjectCycleIds: string[]
currentProjectCompletedCycleIds: string[]
currentProjectIncompleteCycleIds: string[]
currentProjectActiveCycleId: string | null
currentProjectArchivedCycleIds: string[]
currentProjectActiveCycle: ICycle | null
getFilteredCycleIds(projectId, sortByManual)
getCycleById(cycleId): ICycle | null
```

**Actions**:
```typescript
fetchWorkspaceCycles(workspaceSlug)
fetchAllCycles(workspaceSlug, projectId)
fetchActiveCycle(workspaceSlug, projectId)
fetchArchivedCycles(workspaceSlug, projectId)
createCycle(workspaceSlug, projectId, data)
updateCycleDetails(workspaceSlug, projectId, cycleId, data)
deleteCycle(workspaceSlug, projectId, cycleId)
archiveCycle(workspaceSlug, projectId, cycleId)
restoreCycle(workspaceSlug, projectId, cycleId)
```

### API Service

**File**: `apps/web/core/services/cycle.service.ts`

```typescript
class CycleService extends APIService {
  workspaceActiveCyclesAnalytics(workspaceSlug, projectId, cycleId, analyticType)
  workspaceActiveCyclesProgress(workspaceSlug, projectId, cycleId)
  getWorkspaceCycles(workspaceSlug): ICycle[]
  getCyclesWithParams(workspaceSlug, projectId, cycleType?): ICycle[]
  getCycleDetails(workspaceSlug, projectId, cycleId): ICycle
  createCycle(workspaceSlug, projectId, data): ICycle
  patchCycle(workspaceSlug, projectId, cycleId, data): ICycle
  deleteCycle(workspaceSlug, projectId, cycleId): void
  transferIssues(workspaceSlug, projectId, cycleId, { new_cycle_id }): void
}
```

### TypeScript Types

**File**: `packages/types/src/cycle/cycle.ts`

```typescript
type TCycleGroups = "current" | "upcoming" | "completed" | "draft"
type TCycleEstimateType = "issues" | "points"
type TCyclePlotType = "burndown" | "burnup"

interface ICycle extends TProgressSnapshot {
  id: string
  name: string
  description: string
  project_id: string
  start_date: string | null
  end_date: string | null
  status?: TCycleGroups
  archived_at: string | null
  is_favorite?: boolean
  owned_by_id: string
  sort_order: number
  progress_snapshot: TProgressSnapshot | undefined
}
```

---

## Data Flow

### Create Cycle Flow

```
Frontend (UI)
    ↓
CycleStore.createCycle()
    ↓
CycleService.createCycle(POST /api/.../cycles/)
    ↓
CycleListCreateAPIEndpoint.post()
    ├─ Validate dates (both or neither)
    ├─ Check external_id uniqueness
    ├─ Timezone conversion (project timezone → UTC)
    ├─ CycleCreateSerializer.save()
    ├─ Trigger model_activity webhook (Celery)
    └─ Response: CycleSerializer
    ↓
cycleStore.cycleMap[cycleId] = response
    ↓
UI re-renders with updated cycles
```

### Assign Issues to Cycle

```
Frontend
    ↓
CycleService.getCycleIssues() (POST with { issues: [...] })
    ↓
CycleIssueListCreateAPIEndpoint.post()
    ├─ Verify cycle not completed
    ├─ Identify new vs existing issues
    ├─ Bulk create new CycleIssue records
    ├─ Bulk update existing (move from old cycle)
    ├─ Trigger issue_activity webhook
    └─ Response: All CycleIssue objects
    ↓
cycleStore.cycleMap[cycleId] updated with new totals
```

### Transfer Issues & Create Snapshot

```
Frontend (End Cycle action)
    ↓
TransferCycleIssueAPIEndpoint.post()
    ├─ Validate old cycle completed
    ├─ Validate new cycle not completed
    ├─ Call transfer_cycle_issues() utility
    │   ├─ Annotate old_cycle with issue counts
    │   ├─ Calculate assignee distribution
    │   ├─ Calculate label distribution
    │   ├─ Generate burndown_plot() data
    │   └─ Save to Cycle.progress_snapshot
    ├─ Bulk update CycleIssue.cycle_id (incomplete only)
    └─ Trigger issue_activity webhook
```

---

## Error Handling

### Date Validation Errors

| Error | Trigger | HTTP |
|-------|---------|------|
| Both or neither dates | POST/PATCH with partial dates | 400 |
| Start > End | start_date > end_date | 400 |
| Cycle enabled check | cycle_view = False on project | 400 |

### Cycle State Validation Errors

| Error | Trigger | HTTP |
|-------|---------|------|
| Archived edit | PATCH on archived cycle | 400 |
| Completed edit | PATCH (non-sort_order) on completed | 400 |
| Add to completed | POST issues to completed cycle | 400 |
| Transfer from incomplete | Transfer from active cycle | 400 |
| Archive incomplete | Archive non-completed cycle | 400 |

---

## Performance Optimizations

### Query Optimization

```python
.select_related("project", "workspace", "owned_by")
.prefetch_related("issue_cycle__issue__assignees", "issue_cycle__issue__labels")
.annotate(total_issues=Count(...))
.annotate(completed_issues=Count(...))
.distinct()
```

### Soft Delete Pattern

```python
UniqueConstraint(
    fields=["cycle", "issue"],
    condition=Q(deleted_at__isnull=True),
    name="cycle_issue_when_deleted_at_null"
)
```

### Sort Order Optimization

```python
smallest_sort_order = Cycle.objects.filter(project=self.project).aggregate(
    smallest=models.Min("sort_order")
)["smallest"]

if smallest_sort_order is not None:
    self.sort_order = smallest_sort_order - 10000
```

---

## Key Implementation Notes

1. **Date Handling**: All dates stored in UTC; frontend converts to project timezone
2. **Status Derived**: Cycle status computed at query time based on NOW()
3. **Sort Order Float**: Allows unlimited insertions at top without reordering
4. **Completed Immutability**: Once cycle ends, only sort_order can be modified
5. **Progress Snapshot**: Captured when cycle completes; enables viewing metrics after issues deleted
6. **Soft Deletes**: Both CycleIssue and CycleUserProperties use deleted_at

---

## File Reference Map

| Component | File Path |
|-----------|-----------|
| Core Models | `apps/api/plane/db/models/cycle.py` |
| API Views | `apps/api/plane/api/views/cycle.py` |
| Serializers | `apps/api/plane/api/serializers/cycle.py` |
| Transfer Utility | `apps/api/plane/utils/cycle_transfer_issues.py` |
| Frontend Store | `apps/web/core/store/cycle.store.ts` |
| Filter Store | `apps/web/core/store/cycle_filter.store.ts` |
| Frontend Service | `apps/web/core/services/cycle.service.ts` |
| Archive Service | `apps/web/core/services/cycle_archive.service.ts` |
| Type Definitions | `packages/types/src/cycle/cycle.ts` |

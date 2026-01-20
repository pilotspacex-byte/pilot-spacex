# Modules Feature - Comprehensive Architecture Documentation

## Overview

The Modules feature in Plane is a hierarchical organization system that groups related issues into semantic units with timelines, member assignments, and progress tracking. Modules represent high-level feature sets, sprints, or release cycles within a project.

---

## Table of Contents

1. [Data Models](#data-models)
2. [API Endpoints](#api-endpoints)
3. [Business Logic](#business-logic)
4. [Frontend Architecture](#frontend-architecture)
5. [Data Flow](#data-flow)
6. [Integration Points](#integration-points)

---

## Data Models

### Core Module Model

**File**: `apps/api/plane/db/models/module.py`

```python
class Module(ProjectBaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    description_text = models.JSONField()
    description_html = models.JSONField()
    start_date = models.DateField(null=True)
    target_date = models.DateField(null=True)
    status = models.CharField(
        choices=[
            ("backlog", "Backlog"),
            ("planned", "Planned"),
            ("in-progress", "In Progress"),
            ("paused", "Paused"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="planned",
        max_length=20,
    )
    lead = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    members = models.ManyToManyField(User, through="ModuleMember")
    view_props = models.JSONField(default=dict)
    sort_order = models.FloatField(default=65535)
    external_source = models.CharField(max_length=255, null=True)
    external_id = models.CharField(max_length=255, null=True)
    archived_at = models.DateTimeField(null=True)
    logo_props = models.JSONField(default=dict)
```

**Key Fields**:

| Field | Purpose |
|-------|---------|
| `status` | Module lifecycle state (backlog → planned → in-progress → completed/cancelled) |
| `start_date` / `target_date` | Timeline boundaries |
| `lead` | Single user responsible for module |
| `members` | Through-table for module-specific member access |
| `sort_order` | Manual ordering (descending from 65535) |
| `archived_at` | Null = active, non-null = archived |

**Constraints**:
- Module names are unique per project (when not deleted)
- Unique together: `(name, project, deleted_at)`

### ModuleMember Junction Table

```python
class ModuleMember(ProjectBaseModel):
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    member = models.ForeignKey(User, on_delete=models.CASCADE)
```

### ModuleIssue Bridge Table

```python
class ModuleIssue(ProjectBaseModel):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="issue_module")
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="issue_module")
```

### ModuleLink Reference Table

```python
class ModuleLink(ProjectBaseModel):
    title = models.CharField(max_length=255, blank=True, null=True)
    url = models.URLField()
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="link_module")
    metadata = models.JSONField(default=dict)
```

### ModuleUserProperties

```python
class ModuleUserProperties(ProjectBaseModel):
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    filters = models.JSONField(default=get_default_filters)
    display_filters = models.JSONField(default=get_default_display_filters)
    display_properties = models.JSONField(default=get_default_display_properties)
    rich_filters = models.JSONField(default=dict)
```

---

## API Endpoints

### Module CRUD Operations

**Base Path**: `/api/workspaces/{slug}/projects/{project_id}/modules/`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/modules/` | List active modules with pagination |
| POST | `/modules/` | Create new module |
| GET | `/modules/{module_id}/` | Retrieve module details |
| PATCH | `/modules/{module_id}/` | Update module properties |
| DELETE | `/modules/{module_id}/` | Delete module & unlink issues |

### Module-Issue Linking

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/modules/{module_id}/issues/` | List issues in module (paginated) |
| POST | `/modules/{module_id}/issues/` | Bulk add/move issues to module |
| DELETE | `/modules/{module_id}/issues/{issue_id}/` | Remove issue from module |

### Archive Operations

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/archived-modules/` | List archived modules |
| POST | `/modules/{module_id}/archive/` | Archive completed/cancelled module |
| DELETE | `/archived-modules/{module_id}/unarchive/` | Restore archived module |

### Request/Response Examples

**Create Module Request**:
```json
{
  "name": "Q1 2025 Release",
  "description": "First quarter features",
  "start_date": "2025-01-01",
  "target_date": "2025-03-31",
  "status": "planned",
  "lead": "user-uuid",
  "members": ["user-uuid-1", "user-uuid-2"]
}
```

**Module Response (with metrics)**:
```json
{
  "id": "module-uuid",
  "name": "Q1 2025 Release",
  "status": "in-progress",
  "total_issues": 45,
  "completed_issues": 12,
  "cancelled_issues": 2,
  "started_issues": 20,
  "unstarted_issues": 15,
  "backlog_issues": 0,
  "distribution": {
    "assignees": [...],
    "labels": [...],
    "completion_chart": {...}
  }
}
```

---

## Business Logic

### Module Status Lifecycle

```typescript
export const MODULE_STATUS: TModuleStatus[] = [
  "backlog",      // Not scheduled
  "planned",      // Scheduled (default)
  "in-progress",  // Work started
  "paused",       // Temporarily halted
  "completed",    // All work done
  "cancelled"     // Abandoned
];
```

**Status Transitions**:
- Any status → Any status (no restrictions enforced in model)
- Archive-eligible: Only `"completed"` and `"cancelled"` can be archived

### Progress Calculation

```typescript
const completionPercentage =
  ((moduleDetails.completed_issues + moduleDetails.cancelled_issues) / moduleDetails.total_issues) * 100;
const progress = isNaN(completionPercentage) ? 0 : Math.floor(completionPercentage);
```

### Issue Count Annotations

Uses Django ORM annotations to calculate issue counts by state group:

```python
.annotate(
    total_issues=Count(
        "issue_module",
        filter=Q(
            issue_module__issue__archived_at__isnull=True,
            issue_module__issue__is_draft=False,
            issue_module__deleted_at__isnull=True,
        ),
        distinct=True,
    )
)
.annotate(
    completed_issues=Count(
        "issue_module__issue__state__group",
        filter=Q(issue_module__issue__state__group="completed", ...),
        distinct=True,
    )
)
```

### Member Assignment

**Serializer Validation**:
```python
def validate(self, data):
    if data.get("members", []):
        data["members"] = ProjectMember.objects.filter(
            project_id=self.context.get("project_id"),
            member_id__in=data["members"]
        ).values_list("member_id", flat=True)
    return data
```

---

## Frontend Architecture

### MobX Store

**File**: `apps/web/core/store/module.store.ts`

**Observable State**:
```typescript
class ModulesStore {
  loader: boolean = false;
  moduleMap: Record<string, IModule> = {};
  plotType: Record<string, TModulePlotType> = {};
  fetchedMap: Record<string, boolean> = {};
}
```

**Key Computed Properties**:
- `projectModuleIds`: Filter by `project_id`, sort by `sort_order`
- `projectArchivedModuleIds`: Filter by `project_id && archived_at`
- `getFilteredModuleIds`: Apply search + filters from filter store
- `getModuleById`: Single module lookup

**Key Actions**:
```typescript
fetchModules(workspaceSlug, projectId)
fetchModuleDetails(workspaceSlug, projectId, moduleId)
fetchArchivedModules(workspaceSlug, projectId)
createModule(workspaceSlug, projectId, data)
updateModuleDetails(workspaceSlug, projectId, moduleId, data)
deleteModule(workspaceSlug, projectId, moduleId)
archiveModule(workspaceSlug, projectId, moduleId)
restoreModule(workspaceSlug, projectId, moduleId)
createModuleLink(workspaceSlug, projectId, moduleId, data)
updateModuleLink(..., linkId, data)
deleteModuleLink(..., linkId)
```

### API Service

**File**: `apps/web/core/services/module.service.ts`

```typescript
class ModuleService extends APIService {
  getWorkspaceModules(workspaceSlug): Promise<IModule[]>
  getModules(workspaceSlug, projectId): Promise<IModule[]>
  getModuleDetails(workspaceSlug, projectId, moduleId): Promise<IModule>
  createModule(workspaceSlug, projectId, data): Promise<IModule>
  updateModule(workspaceSlug, projectId, moduleId, data): Promise<IModule>
  deleteModule(workspaceSlug, projectId, moduleId): Promise<void>
  getModuleIssues(workspaceSlug, projectId, moduleId, queries?): Promise<TIssuesResponse>
  addIssuesToModule(workspaceSlug, projectId, moduleId, {issues}): Promise<void>
  createModuleLink(workspaceSlug, projectId, moduleId, data): Promise<ILinkDetails>
  updateModuleLink(workspaceSlug, projectId, moduleId, linkId, data): Promise<ILinkDetails>
  deleteModuleLink(workspaceSlug, projectId, moduleId, linkId): Promise<void>
}
```

### TypeScript Types

**File**: `packages/types/src/module/modules.ts`

```typescript
export interface IModule {
  id: string;
  project_id: string;
  workspace_id: string;
  name: string;
  description: string;
  status: TModuleStatus;
  lead_id: string | null;
  member_ids: string[];
  start_date: string | null;
  target_date: string | null;
  archived_at: string | null;
  total_issues: number;
  completed_issues: number;
  cancelled_issues: number;
  started_issues: number;
  unstarted_issues: number;
  backlog_issues: number;
  view_props: { filters: IIssueFilterOptions };
  sort_order: number;
  is_favorite: boolean;
  link_module?: ILinkDetails[];
  distribution?: TModuleDistribution;
}

export type TModuleStatus =
  | "backlog"
  | "planned"
  | "in-progress"
  | "paused"
  | "completed"
  | "cancelled";
```

---

## Data Flow

### Module Creation Flow

```
User Action: "Create Module"
    ↓
ModuleViewHeader (create button)
    ↓
ModuleCreateForm (captures name, dates, lead, members)
    ↓
ModulesStore.createModule(workspaceSlug, projectId, data)
    ↓
Optimistic Update: set(moduleMap, [newId], {...data, id})
    ↓
ModuleService.createModule() [POST /api/.../modules/]
    ↓
Backend: ModuleCreateSerializer validates & creates Module
         + Bulk-creates ModuleMember records
         + Triggers model_activity webhook
    ↓
Success: Merge API response into moduleMap
Error: Rollback moduleMap to previous state
    ↓
UI: List view updates reactively
```

### Issue-to-Module Assignment Flow

```
User Action: "Add issue to module"
    ↓
ModuleService.addIssuesToModule() [POST /api/.../modules/{id}/issues/]
    ↓
Backend: ModuleIssueListCreateAPIEndpoint.post()
         For each issue:
           - Check if ModuleIssue exists
           - If exists & different module: update module_id
           - If not exists: create ModuleIssue record
         - Bulk create/update with batch_size=10
    ↓
Triggers issue_activity webhook with updated module list
    ↓
Frontend:
  - Module.total_issues incremented in distribution
  - ModuleStore.updateModuleDistribution() updates counts
    ↓
UI: Module card shows updated issue count & progress
```

### Archive Flow

```
Module Status: "completed" or "cancelled"
    ↓
User clicks "Archive"
    ↓
ModulesStore.archiveModule()
    ↓
ModuleArchiveService.post() [POST /api/.../modules/{id}/archive/]
    ↓
Backend: Validates status in ["completed", "cancelled"]
         Sets archived_at = timezone.now()
         Deletes from UserFavorite (if starred)
    ↓
Frontend:
  - ModuleStore updates moduleMap[id].archived_at
  - Filters out from projectModuleIds
  - Moves to archived view
```

---

## Integration Points

### With Issue System

- **Issue ↔ Module Linking**: Via `ModuleIssue` bridge table
- **Issue State Changes**: Trigger `updateModuleDistribution()`
- **Issue Deletion**: Cascades to `ModuleIssue` deletion via FK
- **Issue Archive**: Excludes from module counts

### With Project Settings

- **Module View Toggle**: `Project.module_view` boolean
- **External Integrations**: `Module.external_source` & `Module.external_id` for sync

### With User Preferences

- **Favorites**: Via `UserFavorite(entity_type="module")`
- **View Properties**: Stored in `ModuleUserProperties`

---

## Performance Optimizations

### Query Optimization

```python
.select_related("project", "workspace", "lead")
.prefetch_related("members")
.prefetch_related(Prefetch("link_module", queryset=ModuleLink.objects.select_related("module", "created_by")))
```

### Frontend Optimization

**Computed Functions**:
```typescript
getFilteredModuleIds = computedFn((projectId: string) => {
  // MobX cache: only re-runs if dependencies change
})
```

**Lazy Loading**:
- `fetchModulesSlim()` uses cached workspace modules
- `fetchModuleDetails()` only loads when needed

---

## File Reference Map

| Component | File Path |
|-----------|-----------|
| Backend Model | `apps/api/plane/db/models/module.py` |
| Backend API | `apps/api/plane/api/views/module.py` |
| Backend Serializer | `apps/api/plane/api/serializers/module.py` |
| Frontend Store | `apps/web/core/store/module.store.ts` |
| Frontend Service | `apps/web/core/services/module.service.ts` |
| Frontend Types | `packages/types/src/module/modules.ts` |
| Constants | `packages/constants/src/module.ts` |

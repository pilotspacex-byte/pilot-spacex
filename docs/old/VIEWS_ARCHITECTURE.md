# Views (Filtered Issue Lists) Feature - Comprehensive Architecture Documentation

## Overview

The Views feature in Plane provides users with the ability to create, manage, and apply complex filtered issue lists at both project and workspace levels. Views save filter configurations (traditional filters + rich filters), display settings, and display properties, allowing users to quickly access frequently-used issue queries.

---

## Table of Contents

1. [Data Models](#data-models)
2. [API Endpoints](#api-endpoints)
3. [Business Logic](#business-logic)
4. [Frontend Architecture](#frontend-architecture)
5. [Data Flow](#data-flow)
6. [Code Patterns](#code-patterns)

---

## Data Models

### IssueView Model

**File**: `apps/api/plane/db/models/view.py`

```python
class IssueView(WorkspaceBaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    query = models.JSONField()  # Generated from filters
    filters = models.JSONField(default=dict)  # Legacy simple filters
    display_filters = models.JSONField(default=get_default_display_filters)
    display_properties = models.JSONField(default=get_default_display_properties)
    rich_filters = models.JSONField(default=dict)  # Advanced AND/OR logic
    access = models.PositiveSmallIntegerField(default=1, choices=((0, "Private"), (1, "Public")))
    sort_order = models.FloatField(default=65535)
    logo_props = models.JSONField(default=dict)
    owned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="views")
    is_locked = models.BooleanField(default=False)
```

**Key Behavior**:
- On save: `query` is auto-generated from `filters` using `issue_filters()` utility
- Sort order auto-incremented by 10000 when creating new view
- Inherits `workspace_id` and `project_id` from WorkspaceBaseModel

### Default Configurations

**Default Filters**:
```python
{
  "priority": None,
  "state": None,
  "state_group": None,
  "assignees": None,
  "created_by": None,
  "labels": None,
  "start_date": None,
  "target_date": None,
  "subscriber": None,
}
```

**Default Display Filters**:
```python
{
  "group_by": None,
  "order_by": "-created_at",
  "type": None,
  "sub_issue": True,
  "show_empty_groups": True,
  "layout": "list",
  "calendar_date_range": "",
}
```

**Default Display Properties**:
```python
{
  "assignee": True,
  "attachment_count": True,
  "created_on": True,
  "due_date": True,
  "estimate": True,
  "key": True,
  "labels": True,
  "link": True,
  "priority": True,
  "start_date": True,
  "state": True,
  "sub_issue_count": True,
  "updated_on": True,
}
```

---

## API Endpoints

### Project-Level View Endpoints

**Base Path**: `/api/workspaces/{slug}/projects/{project_id}/views/`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/views/` | List all views for project |
| POST | `/views/` | Create new project view |
| GET | `/views/{pk}/` | Get view details |
| PATCH | `/views/{pk}/` | Update view (owner only) |
| DELETE | `/views/{pk}/` | Delete view (admin or owner) |

**Permissions**:
- `list`: ADMIN, MEMBER, GUEST roles
- `retrieve`: ADMIN, MEMBER, GUEST
- `partial_update`: Creator only
- `destroy`: ADMIN role or creator

### Workspace-Level View Endpoints

**Base Path**: `/api/workspaces/{slug}/views/`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/views/` | List workspace views |
| POST | `/views/` | Create workspace-level view |
| GET | `/views/{pk}/` | Get workspace view details |
| PATCH | `/views/{pk}/` | Update workspace view |
| DELETE | `/views/{pk}/` | Delete workspace view |

### Favorite Views Endpoints

**Base Path**: `/api/workspaces/{slug}/projects/{project_id}/user-favorite-views/`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/user-favorite-views/` | List favorite views |
| POST | `/user-favorite-views/` | Add view to favorites |
| DELETE | `/user-favorite-views/{view_id}/` | Remove from favorites |

---

## Business Logic

### Filter Transformation Pipeline

**Backend Flow**:
1. **Filter Input** → `IssueViewSerializer.create()/update()`
2. **Validation** → Check `filters` dict is valid
3. **Transformation** → Call `issue_filters(query_params, method)` utility
4. **Query Generation** → Converts filter dict to Django ORM Q objects
5. **Storage** → Saves both `filters` (original) and `query` (generated)

**Example Transformations**:
```python
# Input filters
{
  "priority": ["high", "urgent"],
  "state": ["uuid1", "uuid2"],
  "assignees": ["user-uuid"]
}

# Generated Django ORM query
{
  "priority__in": ["high", "urgent"],
  "state__in": [UUID("uuid1"), UUID("uuid2")],
  "assignees__in": [UUID("user-uuid")]
}
```

### Rich Filters with AND/OR Logic

**File**: `apps/api/plane/utils/filters/filter_backend.py`

**ComplexFilterBackend** provides advanced JSON-based filtering:

**Filter Structure**:
```json
{
  "and": [
    { "priority__in": "high,urgent" },
    { "state__group__in": "unstarted,started" },
    { "assignee_id__in": "user-1,user-2" }
  ]
}
```

**Gets converted to Django ORM**:
```python
Q(priority__in=["high", "urgent"]) &
Q(state__group__in=["unstarted", "started"]) &
Q(assignee_id__in=["user-1", "user-2"])
```

### Display Filters Options

**Supported Group By**:
- state, priority, labels, created_by, state_detail.group, project
- assignees, cycle, module, target_date, team_project

**Supported Order By**:
- created_at, -created_at, updated_at, -updated_at
- priority, -priority
- assignees__first_name, labels__name
- target_date, estimate_point__key
- link_count, attachment_count, sub_issues_count

**Layout Options**:
- list, kanban, calendar, spreadsheet, gantt_chart

---

## Frontend Architecture

### MobX Stores

#### ProjectViewStore

**File**: `apps/web/core/store/project-view.store.ts`

**Observable State**:
```typescript
loader: boolean;
viewMap: Record<string, IProjectView>;
fetchedMap: Record<string, boolean>;
filters: TViewFilters = {
  searchQuery: "",
  sortBy: "desc",
  sortKey: "updated_at",
  filters?: TViewFilterProps
};
```

**Key Computed Properties**:
- `projectViewIds`: String array of view IDs for current project
- `getProjectViews()`: All views for project (ordered)
- `getFilteredProjectViews()`: Search + filter applied
- `getViewById()`: Single view lookup

**Key Actions**:
```typescript
fetchViews(): Load views from API
createView(): Call service, validate, update store
updateView(): Optimistic update then API call
deleteView(): Remove from store and backend
addViewToFavorites(): Create UserFavorite entry
removeViewFromFavorites(): Delete favorite
```

#### GlobalViewStore

**File**: `apps/web/core/store/global-view.store.ts`

**Observable State**:
```typescript
globalViewMap: Record<string, IWorkspaceView>;
```

**Key Computed Properties**:
- `currentWorkspaceViews`: View IDs for current workspace
- `getSearchedViews()`: Filter by search query
- `getViewDetailsById()`: Single view lookup

### API Service

**File**: `apps/web/core/services/view.service.ts`

```typescript
export class ViewService extends APIService {
  async createView(workspaceSlug, projectId, data): Promise<any>
  async patchView(workspaceSlug, projectId, viewId, data): Promise<any>
  async deleteView(workspaceSlug, projectId, viewId): Promise<any>
  async getViews(workspaceSlug, projectId): Promise<IProjectView[]>
  async getViewDetails(workspaceSlug, projectId, viewId): Promise<IProjectView>
  async addViewToFavorites(workspaceSlug, projectId, data): Promise<any>
  async removeViewFromFavorites(workspaceSlug, projectId, viewId): Promise<any>
}
```

### TypeScript Types

**File**: `packages/types/src/views.ts`

```typescript
export interface IProjectView {
  id: string;
  access: EViewAccess;  // 0=Private, 1=Public
  created_at: Date;
  updated_at: Date;
  is_favorite: boolean;
  name: string;
  description: string;
  rich_filters: TWorkItemFilterExpression;
  display_filters: IIssueDisplayFilterOptions;
  display_properties: IIssueDisplayProperties;
  query: IIssueFilterOptions;
  project: string;
  workspace: string;
  is_locked: boolean;
  owned_by: string;
}

// Rich filter types
export type TWorkItemFilterExpression =
  | TWorkItemFilterConditionData
  | TWorkItemFilterGroup;

export type TWorkItemFilterGroup = {
  [LOGICAL_OPERATOR.AND]: TWorkItemFilterConditionData[];
};

export const WORK_ITEM_FILTER_PROPERTY_KEYS = [
  "state_group", "priority", "start_date", "target_date",
  "assignee_id", "mention_id", "created_by_id", "subscriber_id",
  "label_id", "state_id", "cycle_id", "module_id", "project_id",
  "created_at", "updated_at"
];
```

---

## Data Flow

### Creating a View

```
User Interface
    ↓
ProjectViewStore.createView()
    ↓
ViewService.createView()
    ↓ POST /api/workspaces/{slug}/projects/{projectId}/views/
    ↓
Backend: IssueViewViewSet.perform_create()
    ├─ Set workspace_id, owned_by from context
    ├─ Transform filters using issue_filters()
    ├─ Calculate sort_order (max + 10000)
    └─ Insert into DB
    ↓
Response: IssueViewSerializer
    ↓
ProjectViewStore: Update viewMap[viewId]
    ↓
UI re-renders
```

### Applying View Filters to Issues

```
User clicks view
    ↓
Component: Load view details
    ↓
IssueStore: Get view filters
    ↓
IssueFilterHelperStore.computedFilteredParams()
    ├─ Convert rich_filters to API query params
    └─ Add display_filters
    ↓
Request: GET /api/.../issues/?filters=JSON&order_by=...
    ↓
Backend: ComplexFilterBackend.filter_queryset()
    ├─ Parse filters JSON parameter
    ├─ Build Q objects from filter expression
    ├─ Apply to queryset
    └─ Apply order_by
    ↓
Paginated response
    ↓
Frontend: Update issue store
    ↓
Component: Render filtered issues
```

---

## Code Patterns

### Repository Pattern (Backend)
- **Models** define data structure
- **Serializers** handle validation and transformation
- **ViewSets** implement HTTP endpoints

### Optimistic Updates (Frontend)
```typescript
// 1. Optimistic update
runInAction(() => {
  set(this.viewMap, [viewId], { ...currentView, ...data });
});

// 2. Sync with backend
const response = await this.viewService.patchView(...);

// 3. If error, rollback
```

### JSON Query Serialization
- Filters stored as JSON in DB
- Complex AND/OR expressions supported
- Client-agnostic filtering logic

### Permission-Based Filtering
Views filtered based on:
- User role (ADMIN, MEMBER, GUEST)
- Guest view all features flag
- View ownership (creator can modify)
- Project membership

---

## Integration Points

### Upstream (Who Calls Views)
- View Selector Components
- Filter Panels
- Issue List Views
- Sidebar/Navigation

### Downstream (What Views Call)
- Issue Models & API
- User Favorites Store
- Filter Utilities
- Recent Visit Tracker

### Database Relationships

```
Workspace
  ├─ IssueView (workspace views, project_id=NULL)
  │  ├─ owned_by → User
  │  └─ workspace → Workspace
  └─ Project
     ├─ IssueView (project views)
     └─ Issue (filtered by view)

UserFavorite
  ├─ entity_type = "view"
  ├─ entity_identifier = IssueView.id
  └─ project → Project
```

---

## File Reference Map

| Component | File Path |
|-----------|-----------|
| Backend Model | `apps/api/plane/db/models/view.py` |
| Backend Views | `apps/api/plane/app/views/view/base.py` |
| Backend Serializers | `apps/api/plane/app/serializers/view.py` |
| Filter Backend | `apps/api/plane/utils/filters/filter_backend.py` |
| Frontend Service | `apps/web/core/services/view.service.ts` |
| Project View Store | `apps/web/core/store/project-view.store.ts` |
| Global View Store | `apps/web/core/store/global-view.store.ts` |
| Type Definitions | `packages/types/src/views.ts` |
| Filter Helper | `apps/web/core/store/issue/helpers/issue-filter-helper.store.ts` |

# API Contracts: Project Notes Panel (022)

**Date**: 2026-03-10
**Note**: All contracts below use **existing** backend endpoints. No new API endpoints are required for this feature.

---

## Contract 1: List Pinned Project Notes

**Endpoint**: `GET /api/v1/workspaces/{workspaceId}/notes`
**Auth**: Required (Bearer token via Supabase Auth)
**RLS**: User must be a member of the workspace

### Query Parameters

| Param | Type | Required | Description |
|---|---|---|---|
| `project_id` | UUID string | Yes | Filter to project-linked notes only |
| `is_pinned` | boolean | Yes (`true`) | Filter to pinned notes only |
| `pageSize` | integer (1–100) | No (default 20) | Set to `5` for panel |
| `cursor` | string | No | Omit for first page |

### Response `200 OK`

```json
{
  "items": [
    {
      "id": "uuid",
      "title": "string",
      "isPinned": true,
      "projectId": "uuid",
      "updatedAt": "2026-03-10T12:00:00Z",
      "wordCount": 420,
      "topics": []
    }
  ],
  "total": 3,
  "hasNext": false,
  "hasPrev": false,
  "nextCursor": null,
  "prevCursor": null,
  "pageSize": 5
}
```

### Error Responses

| Status | Condition |
|---|---|
| `401` | Missing or invalid auth token |
| `403` | User not a workspace member |
| `404` | Workspace not found |

---

## Contract 2: List Recent Project Notes (not pinned)

**Endpoint**: `GET /api/v1/workspaces/{workspaceId}/notes`
**Identical to Contract 1** except `is_pinned=false`.

---

## Contract 3: Create Project-Linked Note

**Endpoint**: `POST /api/v1/workspaces/{workspaceId}/notes`
**Auth**: Required (Bearer token)
**Permission**: Role must not be `guest`

### Request Body

```json
{
  "title": "Untitled",
  "workspaceId": "uuid",
  "projectId": "uuid"
}
```

### Response `201 Created`

```json
{
  "id": "uuid",
  "title": "Untitled",
  "isPinned": false,
  "projectId": "uuid",
  "workspaceId": "uuid",
  "wordCount": 0,
  "createdAt": "2026-03-10T12:00:00Z",
  "updatedAt": "2026-03-10T12:00:00Z"
}
```

### Error Responses

| Status | Condition |
|---|---|
| `401` | Unauthenticated |
| `403` | Guest role (cannot create content) |
| `422` | Validation error (missing `title` or `workspaceId`) |

---

## Component Interface Contract

### `ProjectNotesPanel` Props

```typescript
interface ProjectNotesPanelProps {
  /** Project entity from useProject hook */
  project: Project;
  /** Workspace slug for building note URLs */
  workspaceSlug: string;
  /** Workspace UUID for API calls */
  workspaceId: string;
}
```

### Behaviour Contract

| State | Panel renders |
|---|---|
| Loading (either query) | 3 skeleton rows per sub-section |
| Error (either query) | Inline "Failed to load notes" text (non-crashing) |
| Empty (no notes at all) | Empty state with "New Note" link |
| Has pinned notes | "Pinned" section header + up to 5 rows |
| Has recent notes (no pinned) | "Recent" section header + up to 5 rows |
| Has > 5 notes in either section | Shows 5 rows + "View all" link |
| Create note pending | "New Note" button shows loading state |

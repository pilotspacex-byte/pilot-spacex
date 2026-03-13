# API Contracts: Project Notes Panel (022)

**Date**: 2026-03-10
**Updated**: 2026-03-10 — v3: new move endpoint + updated create response type
**Note**: v3 adds 1 new endpoint and modifies 1 existing endpoint response type.

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

> **v3 CHANGE**: Response type changed from `NoteResponse` to `NoteDetailResponse` — now includes `content` field.

```json
{
  "id": "uuid",
  "title": "Untitled",
  "isPinned": false,
  "projectId": "uuid",
  "workspaceId": "uuid",
  "wordCount": 0,
  "content": {
    "type": "doc",
    "content": [{ "type": "paragraph" }]
  },
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

## Contract 4 (NEW): Move Note to Project

**Endpoint**: `POST /api/v1/workspaces/{workspaceId}/notes/{noteId}/move`
**Auth**: Required (Bearer token)
**Permission**: Role must not be `guest`

### Path Parameters

| Param | Type | Description |
|---|---|---|
| `workspaceId` | UUID or slug | Workspace |
| `noteId` | UUID | Note to move |

### Request Body

```json
{
  "project_id": "uuid-or-null"
}
```

- `project_id: UUID` — moves note to the specified project
- `project_id: null` — removes project association (moves to root workspace)

### Response `200 OK`

```json
{
  "id": "uuid",
  "title": "string",
  "isPinned": false,
  "projectId": "uuid-or-null",
  "workspaceId": "uuid",
  "wordCount": 0,
  "updatedAt": "2026-03-10T12:01:00Z",
  "createdAt": "2026-03-10T12:00:00Z"
}
```

### Error Responses

| Status | Condition |
|---|---|
| `401` | Unauthenticated |
| `403` | Guest role or not a workspace member |
| `404` | Note or workspace not found |
| `422` | Missing `project_id` field in body |

---

## Component Interface Contract (v3 updates)

### `TemplatePicker` Props (updated)

```typescript
interface TemplatePickerProps {
  workspaceId: string;
  isAdmin: boolean;
  onConfirm: (template: NoteTemplate | null, projectId: string | null) => void;  // CHANGED
  onClose: () => void;
}
```

### `MoveNoteDialog` Props (unchanged, search added internally)

```typescript
interface MoveNoteDialogProps {
  workspaceId: string;
  currentProjectId?: string | null;
  confirmLabel?: string;
  onSelect: (projectId: string | null) => void;
  onClose: () => void;
}
```

### `ProjectNotesPanel` Behaviour Contract (v3 update)

| State | Panel renders |
|---|---|
| Loading (recent query) | 3 skeleton rows |
| Error | Inline "Failed to load notes" text (non-crashing) |
| Empty (no notes) | Empty state |
| Has recent notes | "Recent" section header + up to 5 rows |
| Has > 5 recent notes | Shows 5 rows + "View all" link |
| **Pinned section** | **Removed (v3 BUG-2)** |


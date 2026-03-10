# Data Model: Project Notes Panel (022)

**Date**: 2026-03-10

This feature is **frontend-only** — no new backend models, migrations, or API endpoints. All data already exists.

---

## Entities Used

### Note (existing)

Relevant fields consumed by the panel:

| Field | Type | Notes |
|---|---|---|
| `id` | `string` (UUID) | Navigation link key |
| `title` | `string` | Displayed in panel row (truncated to 1 line) |
| `isPinned` | `boolean` | Determines Pinned vs Recent sub-section |
| `projectId` | `string?` | Filter: only notes where `projectId === project.id` |
| `updatedAt` | `string` (ISO) | Sort order for Recent sub-section |

Source: `frontend/src/types/note.ts`

### Project (existing)

Relevant fields consumed by the panel:

| Field | Type | Notes |
|---|---|---|
| `id` | `string` (UUID) | Used as `projectId` filter in API call |
| `workspaceId` | `string` (UUID) | Used to build `workspaceSlug`-based note links |

Source: `frontend/src/types/workspace.ts`

---

## Data Flow

```
ProjectSidebar
  └── ProjectNotesPanel (props: project, workspaceSlug, workspaceId)
        ├── useNotes({ workspaceId, projectId: project.id, isPinned: true, pageSize: 5 })
        │     → TanStack Query → GET /workspaces/{id}/notes?project_id=X&is_pinned=true&pageSize=5
        │     → pinnedNotes: Note[]
        └── useNotes({ workspaceId, projectId: project.id, isPinned: false, pageSize: 5 })
              → TanStack Query → GET /workspaces/{id}/notes?project_id=X&is_pinned=false&pageSize=5
              → recentNotes: Note[]
```

---

## API Calls (existing endpoints, no changes)

### List pinned project notes
```
GET /api/v1/workspaces/{workspaceId}/notes
  ?project_id={projectId}
  &is_pinned=true
  &pageSize=5
```

### List recent project notes (not pinned)
```
GET /api/v1/workspaces/{workspaceId}/notes
  ?project_id={projectId}
  &is_pinned=false
  &pageSize=5
```

### Create project-linked note
```
POST /api/v1/workspaces/{workspaceId}/notes
Body: {
  "title": "Untitled",
  "workspaceId": "{workspaceId}",
  "projectId": "{projectId}"
}
```

All endpoints are authenticated (Supabase Auth header) and RLS-enforced.

---

## State (UI only, no persistent state)

| State | Location | Type |
|---|---|---|
| Loading (pinned) | TanStack Query | `boolean` |
| Loading (recent) | TanStack Query | `boolean` |
| Error (pinned) | TanStack Query | `Error \| null` |
| Error (recent) | TanStack Query | `Error \| null` |
| Create pending | TanStack Query mutation | `boolean` |

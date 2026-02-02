# Data Model: Issue Detail Page

**Feature**: 007-issue-detail-page
**Date**: 2026-02-02

---

## Overview

This feature is **primarily frontend** — no new database tables. However, several assumed backend endpoints **do not exist** (comment edit/delete, integration-links list, note-links list, labels list, sub-issues list). Components referencing missing endpoints render empty state or use workarounds. This document maps the actual backend response schemas to frontend TypeScript interfaces.

---

## Frontend TypeScript Interfaces

### Issue (aligned with backend `IssueResponse`)

```typescript
// Must match backend IssueResponse from backend/src/pilot_space/api/v1/schemas/issue.py
interface Issue {
  id: string;
  workspaceId: string;        // backend: workspace_id
  sequenceId: number;          // e.g., 123 in PS-123
  identifier: string;          // e.g., "PS-123"

  // Core fields — NOTE: backend uses `name`, not `title`
  name: string;                // 1-255 chars (backend field name)
  description: string | null;
  descriptionHtml: string | null;  // backend: description_html

  // Workflow
  state: StateBrief;           // Object { id, name, color, group }, NOT string enum
  priority: IssuePriority;     // 'urgent' | 'high' | 'medium' | 'low' | 'none'
  estimatePoints: number | null;  // backend: estimate_points (Fibonacci: 1,2,3,5,8,13)
  startDate: string | null;    // backend: start_date (ISO date)
  targetDate: string | null;   // backend: target_date (ISO date, serves as due date)
  sortOrder: number;           // backend: sort_order

  // Relations (from backend response)
  project: ProjectBrief;       // { id, name, identifier }
  assignee: UserBrief | null;  // { id, email, displayName }
  reporter: UserBrief;         // { id, email, displayName } — always present
  labels: LabelBrief[];        // { id, name, color }

  // AI metadata
  aiMetadata: Record<string, unknown> | null;
  hasAiEnhancements: boolean;  // backend: has_ai_enhancements

  // Counts
  subIssueCount: number;       // backend: sub_issue_count (count only, no children list)

  // Timestamps
  createdAt: string;
  updatedAt: string;

  // NOT in backend response (frontend-only or future):
  // type: IssueType;           // Not in IssueResponse — frontend-only field
  // cycleId: string | null;    // Not in IssueResponse (only in IssueUpdateRequest)
  // moduleId: string | null;   // Not in IssueResponse
  // parentId: string | null;   // Not in IssueResponse
  // children: IssueSummary[];  // Not in IssueResponse (only sub_issue_count)
  // integrationLinks: [];      // Not in IssueResponse (no endpoint)
  // noteLinks: [];             // Not in IssueResponse (no endpoint)
}
```

### Activity (aligned with backend `ActivityResponse`)

```typescript
// Must match backend ActivityResponse from backend/src/pilot_space/api/v1/schemas/issue.py
interface Activity {
  id: string;

  // Action type
  activityType: string;       // backend: activity_type (e.g., 'commented', 'state_changed', 'assigned')

  // Actor
  actor: UserBrief | null;    // Can be null for system-generated activities

  // Change tracking
  field: string | null;       // Which field changed
  oldValue: string | null;    // Previous value
  newValue: string | null;    // New value

  // Comment content (plain text only)
  comment: string | null;     // Comment text — NOT HTML

  // Metadata
  metadata: Record<string, unknown> | null;  // May contain AI-related info

  // Timestamp
  createdAt: string;

  // NOT in backend response:
  // workspaceId: string;     // Not returned
  // issueId: string;         // Not returned
  // verb: ActivityVerb;      // Backend uses `activityType` string
  // isAiGenerated: boolean;  // Not in backend — check metadata if needed
  // commentHtml: string;     // Backend only returns plain `comment`
  // editedAt: string;        // No comment edit tracking in backend
  // deletedAt: string;       // No comment soft-delete in backend
}

interface ActivityTimelineResponse {
  activities: Activity[];
  total: number;              // Total count for offset-based pagination
}
```

### IntegrationLink (frontend-only type — no backend endpoint)

```typescript
// NOTE: No dedicated GET endpoint exists for integration links.
// IssueResponse does NOT include integrationLinks array.
// This type is defined for future use when backend adds support.
interface IntegrationLink {
  id: string;
  issueId: string;
  integrationType: 'github_pr' | 'github_issue' | 'slack';
  externalId: string;
  externalUrl: string;

  // GitHub PR specific
  prNumber: number | null;
  prTitle: string | null;
  prStatus: 'open' | 'merged' | 'closed' | null;
}
```

### NoteIssueLink (frontend-only type — no backend endpoint)

```typescript
// NOTE: No dedicated GET endpoint exists for note-issue links.
// IssueResponse does NOT include noteLinks array.
// This type is defined for future use when backend adds support.
interface NoteIssueLink {
  id: string;
  noteId: string;
  issueId: string;
  linkType: 'CREATED' | 'EXTRACTED' | 'REFERENCED';

  // Denormalized note info for sidebar display
  noteTitle: string;
}
```

### Supporting Types (aligned with backend schemas)

```typescript
// Matches backend UserBriefSchema
interface UserBrief {
  id: string;
  email: string;
  displayName: string | null;  // backend: display_name
}

// Matches backend StateBriefSchema
interface StateBrief {
  id: string;
  name: string;
  color: string;
  group: StateGroup;           // 'backlog' | 'unstarted' | 'started' | 'completed' | 'cancelled'
}

// Matches backend LabelBriefSchema
interface LabelBrief {
  id: string;
  name: string;
  color: string;
}

// Matches backend ProjectBriefSchema
interface ProjectBrief {
  id: string;
  name: string;
  identifier: string;
}

// Matches backend IssueBriefResponse
interface IssueBriefResponse {
  id: string;
  identifier: string;
  name: string;                // NOTE: `name`, not `title`
  priority: IssuePriority;
  state: StateBrief;           // Object, not string
  assignee: UserBrief | null;
}

// Frontend Cycle type (already exists in frontend/src/types/index.ts)
// Note: cyclesApi.list() requires projectId, not workspace-scoped
interface Cycle {
  id: string;
  workspaceId: string;
  name: string;
  description?: string;
  status: CycleStatus;
  startDate?: string;
  endDate?: string;
  sequence: number;
  project: ProjectBrief;
  ownedBy?: User;
  metrics?: CycleMetrics;
  issueCount: number;
}

type StateGroup = 'backlog' | 'unstarted' | 'started' | 'completed' | 'cancelled';
type IssuePriority = 'urgent' | 'high' | 'medium' | 'low' | 'none';
type IssueType = 'bug' | 'feature' | 'task' | 'improvement';  // Frontend-only, not in backend
type CycleStatus = 'draft' | 'planned' | 'active' | 'completed' | 'cancelled';
```

---

## API Endpoint Mapping

### Verified Endpoints (exist in backend)

| Frontend Action | HTTP Method | Endpoint | Request Body | Response |
|----------------|-------------|----------|--------------|----------|
| Load issue | GET | `/api/v1/workspaces/{wid}/issues/{iid}` | — | `IssueResponse` |
| Update issue | PATCH | `/api/v1/workspaces/{wid}/issues/{iid}` | `IssueUpdateRequest` (name, state_id, priority, estimate_points, etc.) | `IssueResponse` |
| List activities | GET | `/api/v1/workspaces/{wid}/issues/{iid}/activities?limit=50&offset=0` | — | `ActivityTimelineResponse` { activities[], total } |
| Add comment | POST | `/api/v1/workspaces/{wid}/issues/{iid}/comments` | `{ content }` (1-10000 chars) | `ActivityResponse` |
| Create sub-issue | POST | `/api/v1/workspaces/{wid}/issues` | `IssueCreateRequest` with `parent_id` | `IssueResponse` |
| List cycles | GET | `/api/v1/workspaces/{wid}/cycles?project_id={pid}` | — | `CycleListResponse` (requires project_id) |
| List workspace members | GET | `/api/v1/workspaces/{wid}/members` | — | `Member[]` |

### Missing Endpoints (NOT in backend — descoped or use workarounds)

| Frontend Action | Expected Endpoint | Status | Workaround |
|----------------|-------------------|--------|------------|
| Edit comment | PATCH `.../comments/{cid}` | NOT IMPLEMENTED | Descoped from MVP |
| Delete comment | DELETE `.../comments/{cid}` | NOT IMPLEMENTED | Descoped from MVP |
| List labels | GET `.../labels` | NOT IMPLEMENTED | Use labels from issue response |
| List sub-issues | GET `.../issues?parent_id={pid}` | PARTIAL | Filter issues by parent_id via list endpoint |
| List integration links | GET `.../issues/{iid}/integration-links` | NOT IMPLEMENTED | Empty state in component |
| List note links | GET `.../issues/{iid}/note-links` | NOT IMPLEMENTED | Empty state in component |

---

## State Management Mapping

| Data | Store Type | Justification |
|------|-----------|---------------|
| Issue data (title, description, properties) | TanStack Query | Server state; caching, invalidation |
| Activities list | TanStack Query (`useInfiniteQuery`) | Paginated server state |
| Workspace members | TanStack Query | Shared across components |
| Available labels | TanStack Query | Shared across components |
| Available cycles | TanStack Query | Shared across components |
| Edit mode flags (isEditingTitle, etc.) | MobX (IssueStore) | UI-only state |
| Save status per field | MobX (IssueStore) | UI-only state |
| AI Context sidebar open | MobX (IssueStore) or useState | UI-only state |
| Dirty title/description text | useState (local) | Component-local editing state |

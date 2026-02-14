# Homepage Hub Module

_For project overview, see main `CLAUDE.md` and `frontend/CLAUDE.md`_

## Purpose

Primary landing page after workspace selection (US-19 / H047). Embodies Note-First workflow (DD-013) with compact AI chat, activity feed, and AI digest panel -- not a traditional dashboard.

**Entry**: Login -> `/` -> resolve workspace -> `/{workspaceSlug}` -> HomepageHub (no redirect to `/notes`).

---

## Three-Zone Layout

```
+-----------------------------------------------------------+
|          Zone 1: Compact ChatView (H035-H040)              |
|  Collapsed: 48px input bar. Expanded: 400px chat panel.   |
+-----------------------------------------------------------+
|  Zone 2: Activity Feed     |  Zone 3: AI Digest Panel     |
|  (H033, H034)              |  (H041, H046)                |
|  Recent notes & issues     |  12-category AI suggestions  |
|  grouped by time.          |  Dismissible. Refresh.       |
|  Infinite scroll (20/page) |  Stale time: 5 min           |
+-----------------------------------------------------------+
Desktop: flex-[3] activity, flex-[2] digest
Mobile: Stacked vertically
```

---

## Component Hierarchy

```
WorkspaceHomePage (wrapper)
└── HomepageHub (3-zone orchestrator)
    ├── CompactChatView (H035-H040)
    │   ├── CompactChatInput (collapsed 48px)
    │   └── CompactChatPanel (expanded, message history)
    ├── ActivityFeed (H033, infinite scroll)
    │   ├── DayGroupHeader (Today, Yesterday, This Week)
    │   ├── NoteActivityCard
    │   └── IssueActivityCard
    └── DigestPanel (H046)
        ├── DigestSuggestionCard
        ├── DigestEmptyState
        └── DigestSkeleton
```

---

## Features

### Compact ChatView (Zone 1)

**Collapsed** (48px): Input bar with AI avatar, placeholder, `[/]` hint. **Expanded** (400px): Chat history + input + send/abort. Transitions: click to expand (200ms), ESC/outside to collapse. Mobile: bottom sheet with backdrop.

### Activity Feed (Zone 2)

Time-grouped (Today, Yesterday, This Week -- non-empty buckets only). 20 items/page cursor-based, IntersectionObserver sentinel, max 200 rendered. Card types: NoteActivityCard (title, project, word count) and IssueActivityCard (ID, state badge, priority, assignee). Empty: "Your workspace is quiet." Query: 30s stale, 5min GC, refetch on focus.

### AI Digest Panel (Zone 3)

12 suggestion categories: stale issues, missing docs, inconsistent status, blocked deps, unassigned work, overdue cycle items, PR review pending, duplicate candidates, note refinement, project health, knowledge gaps, release readiness. Relevance score (0-1), dismiss, action link. 5min stale, 10min GC, no refetch on focus.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `/` | Focus chat input (if not typing) |
| `F6` / `Shift+F6` | Cycle zones forward/backward |
| `Escape` | Close expanded chat |
| `Tab` | Focus trap in chat (when expanded) |

ARIA landmarks on all three zones. Reduced motion support via CSS media query.

---

## API Endpoints

**Activity**: `GET /api/v1/workspaces/{id}/homepage/activity?cursor=` -> `{ data: Record<bucket, ActivityCard[]>, meta: { total, cursor, has_more } }`

**Digest**: `GET /api/v1/workspaces/{id}/homepage/digest` -> `{ data: { generated_at, suggestions[] } }`

**Refresh**: `POST .../digest/refresh` -> `{ status }`. **Dismiss**: `POST .../digest/dismiss` with `{ suggestion_id, category, entity_id }`.

---

## Hooks & Store

**Hooks**: `useHomepageActivity` (infinite query), `useWorkspaceDigest` (digest query), `useCompactChat` (bridge to PilotSpaceStore), `useDigestDismiss` (dismiss mutation).

**HomepageUIStore** (MobX): `chatExpanded`, `activeZone` (for F6 cycling). Actions: `expandChat()`, `collapseChat()`, `toggleChat()`, `setActiveZone()`, `reset()`.

---

## File Structure

```
frontend/src/features/homepage/
├── index.ts, types.ts, constants.ts
├── stores/HomepageUIStore.ts
├── api/homepage-api.ts
├── hooks/ (4 hooks)
├── components/
│   ├── HomepageHub.tsx (~140 lines)
│   ├── CompactChatView/
│   ├── ActivityFeed/
│   └── DigestPanel/
└── __tests__/ (9 test files)
```

---

## Related Documentation

- **DD-013**: Note-First workflow
- **DD-065**: MobX + TanStack Query
- **DD-086**: Centralized PilotSpaceAgent
- **US-19**: Homepage Hub feature

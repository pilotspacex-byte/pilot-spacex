# Architecture Research

**Domain:** Notion-style page tree, project-centric navigation, embedded issue views, responsive layout
**Researched:** 2026-03-12
**Confidence:** HIGH (based on thorough analysis of existing codebase)

## System Overview

```
Current Architecture (unchanged layers)
========================================
Frontend: Next.js 15 App Router + MobX + TanStack Query + shadcn/ui
Backend:  FastAPI 5-layer Clean Architecture + SQLAlchemy async + DI
Database: PostgreSQL 16 + RLS + pgvector + pgmq
Auth:     Supabase Auth + JWT + RLS policies

New Components (this milestone)
========================================
                    +--------------------------+
                    |   Sidebar (MODIFIED)     |
                    |   +-- ProjectTree        | NEW: expandable 3-level tree
                    |   +-- PersonalPages      | NEW: user-level pages section
                    |   +-- PinnedRecent       | EXISTING: keep as-is
                    +--------------------------+
                              |
              +---------------+---------------+
              |                               |
    +-------------------+          +--------------------+
    | Project Hub Page  |          | Notes Page         |
    | (MODIFIED)        |          | (MODIFIED)         |
    | +-- PageTree      | NEW      | +-- PersonalPages  | NEW
    | +-- IssueViews    | NEW      +--------------------+
    |   +-- Board       |
    |   +-- List        |
    |   +-- Timeline    |
    |   +-- Priority    |
    +-------------------+
              |
    +-------------------+
    | Page Editor       |
    | (MODIFIED Note)   | note.py gains parent_id, depth, position
    +-------------------+
```

### Component Responsibilities

| Component | Responsibility | Status | Key Files |
|-----------|----------------|--------|-----------|
| `Note` model | Document storage with tree hierarchy | MODIFY | `backend/.../models/note.py` |
| `Project` model | Project container | KEEP | `backend/.../models/project.py` |
| `Sidebar` | Workspace navigation | MODIFY | `frontend/src/components/layout/sidebar.tsx` |
| `ProjectTreeStore` | MobX store for project page trees | NEW | `frontend/src/stores/features/projects/` |
| `PageTreeComponent` | Recursive tree with drag/indent | NEW | `frontend/src/features/projects/components/` |
| `IssueViewTabs` | Board/List/Timeline/Priority tabs | NEW | `frontend/src/features/projects/components/` |
| `AppShell` | Layout shell with responsive sidebar | MODIFY | `frontend/src/components/layout/app-shell.tsx` |

## Database Schema Changes

### 1. Note Model: Add Tree Hierarchy (Migration ~062)

The `Note` model already has `project_id` (nullable FK to projects) and `owner_id` (FK to users). Add three columns to enable the page tree:

```python
# New columns on notes table
parent_id: Mapped[uuid.UUID | None] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("notes.id", ondelete="CASCADE"),
    nullable=True,
)
depth: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=0,
    server_default=text("0"),
)
position: Mapped[float] = mapped_column(
    # Float for fractional indexing (insert between without reorder)
    Numeric(10, 4),
    nullable=False,
    default=0,
    server_default=text("0"),
)
```

**Depth constraint**: Enforce max depth = 2 (0-indexed: root=0, child=1, grandchild=2) at the application layer via a CHECK constraint in the migration:

```sql
ALTER TABLE notes ADD CONSTRAINT chk_notes_depth CHECK (depth >= 0 AND depth <= 2);
```

**Self-referential relationship** on Note model:

```python
parent: Mapped[Note | None] = relationship(
    "Note",
    remote_side="Note.id",
    back_populates="children",
    lazy="selectin",
)
children: Mapped[list[Note]] = relationship(
    "Note",
    back_populates="parent",
    cascade="all, delete-orphan",
    lazy="selectin",
    order_by="Note.position",
)
```

**New indexes**:

```python
Index("ix_notes_parent_id", "parent_id"),
Index("ix_notes_position", "position"),
Index("ix_notes_project_depth", "project_id", "depth"),
```

**RLS**: No new policies needed -- notes already have workspace_id RLS via `WorkspaceScopedModel`. The `parent_id` self-reference stays within the same workspace (enforced by the FK + existing RLS).

### 2. Two Ownership Models

The current `Note` model already supports both patterns:

| Ownership | How It Works | Query Pattern |
|-----------|-------------|---------------|
| **Project page** | `project_id IS NOT NULL`, `parent_id` forms tree within project | `WHERE project_id = :pid AND parent_id IS NULL` for roots |
| **Personal page** | `project_id IS NULL`, `owner_id = current_user` | `WHERE project_id IS NULL AND owner_id = :uid AND parent_id IS NULL` |

No new table needed. The distinction is purely `project_id IS NULL` vs `project_id IS NOT NULL`. Workspace-level notes (current) become personal pages by convention (they already have `owner_id`).

**Migration**: Existing notes with `project_id IS NULL` need no data migration -- they naturally become personal pages. Set `depth = 0` and `position` based on `created_at` ordering for all existing notes.

### 3. No Changes to Issue/Project Models

Issues already belong to projects (`project_id` NOT NULL). The embedded issue database views are purely frontend -- they query `GET /workspaces/{wid}/projects/{pid}/issues` with different grouping/sorting parameters. No schema changes needed.

## Frontend Architecture Changes

### Pattern 1: Project Tree Store (MobX)

**What:** A new `ProjectTreeStore` that loads the page tree for a project and manages expand/collapse state, reordering, and reparenting.

**When to use:** Sidebar project tree sections, project hub page tree panel.

**Why MobX over TanStack Query for this:** Tree state (expanded nodes, drag positions, optimistic reorder) is complex interactive state -- MobX excels here. TanStack Query handles the server fetch; MobX manages the tree UI state. This matches the existing NoteStore pattern.

```typescript
// frontend/src/stores/features/projects/ProjectTreeStore.ts
class ProjectTreeStore {
  // Map<projectId, TreeNode[]> -- root nodes per project
  trees: Map<string, TreeNode[]> = new Map();
  // Set<noteId> -- which nodes are expanded in sidebar
  expandedNodes: Set<string> = new Set();
  // Currently dragging node
  draggingNodeId: string | null = null;

  async loadTree(projectId: string): Promise<void> { /* GET /projects/:id/pages */ }
  toggleExpand(nodeId: string): void { /* toggle in expandedNodes set */ }
  async movePage(pageId: string, newParentId: string | null, newPosition: number): Promise<void> {
    // Optimistic update -> PATCH /notes/:id { parent_id, position }
  }
}

interface TreeNode {
  id: string;
  title: string;
  parentId: string | null;
  depth: number;
  position: number;
  children: TreeNode[];
  icon?: string;
}
```

**Persist expanded state** in `localStorage` keyed by `pilot-space:tree-expanded:{workspaceId}` to survive page reloads.

### Pattern 2: Sidebar Project Tree Section

**What:** Replace the flat "Notes" section in the sidebar (currently Pinned/Recent notes) with a project-centric tree.

**Current sidebar structure** (`sidebar.tsx` L86-L114):
```
Main: Home, Notes, Issues, Projects, Members
AI: Chat, Skill, Costs, Approvals
---
Pinned Notes (flat list)
Recent Notes (flat list)
---
New Note button
```

**New sidebar structure:**
```
Main: Home, Notes*, Issues, Projects, Members
AI: Chat, Skill, Costs, Approvals
---
Projects (expandable per-project trees):
  Project Alpha
    > Page 1
      > Sub-page 1a
      > Sub-page 1b
    > Page 2
  Project Beta
    > Page 3
---
Pinned (pages from any project or personal)
Recent (last 5 visited pages)
---
New Page button (context-aware: project page or personal page)
```

*"Notes" link becomes personal pages view; the top-level item label may change to "My Pages" but the route stays `/notes`.*

**Implementation approach:**

1. **New component `SidebarProjectTree`**: Renders a collapsible section per project. Each project header is expandable and shows its page tree (max 3 levels). Uses `ProjectTreeStore.expandedNodes` for state.

2. **Modify `Sidebar` component** (currently 671 lines): Extract the Pinned/Recent sections into a `SidebarShortcuts` sub-component. Add `SidebarProjectTree` between the main nav and shortcuts. This keeps `sidebar.tsx` under the 700-line limit.

3. **Collapsed sidebar**: In collapsed mode, projects show only the project icon. Hovering shows a tooltip flyout with the tree -- same pattern as current collapsed nav items use `Tooltip`.

### Pattern 3: Embedded Issue Database Views

**What:** Tab-based issue views (Board, List, Timeline, Priority) embedded inside the project hub page.

**Current state:** Issues page at `/{ws}/issues` shows a cross-project issue list. Individual project pages at `/{ws}/projects/{pid}` show project overview.

**New state:** Project hub page gains a tabbed section below the page tree showing project issues in different views:

```
/{ws}/projects/{pid}
  +-- Page Tree Panel (left or top)
  +-- Issue Views (tabs: Board | List | Timeline | Priority)
```

**Reuse existing components:** The current issue list page (`/{ws}/issues`) has sorting, filtering, and grouping logic. Factor out the issue rendering into reusable view components:

| View | Component | Data Source |
|------|-----------|-------------|
| Board | `IssueBoardView` | `GET /projects/{pid}/issues?group_by=state` |
| List | `IssueListView` | `GET /projects/{pid}/issues?sort_by=...` |
| Timeline | `IssueTimelineView` | `GET /projects/{pid}/issues` + `start_date`/`target_date` |
| Priority | `IssuePriorityView` | `GET /projects/{pid}/issues?group_by=priority` |

**No new API endpoints needed.** The existing `GET /workspaces/{wid}/projects/{pid}/issues` already supports filtering and sorting. The views are purely frontend presentation variations.

**Timeline view** requires `start_date` and `target_date` on issues, which already exist in the Issue model. Use a horizontal Gantt-style layout with shadcn/ui primitives.

### Pattern 4: Responsive Layout

**What:** Desktop (1280px+) and tablet (768-1024px) responsive layout.

**Current state:** `AppShell` already handles responsive layout:
- `useResponsive()` hook provides `isMobile`, `isTablet`, `isDesktop`, `isSmallScreen`
- Sidebar is overlay on `isSmallScreen` (mobile + tablet), inline on desktop
- `UIStore` persists `sidebarCollapsed` and `sidebarWidth`

**Changes needed:**

1. **Tablet sidebar behavior** (768-1024px): Currently grouped with mobile as `isSmallScreen`. Split tablet behavior:
   - Tablet: sidebar defaults collapsed (icon rail, 60px), can expand to overlay
   - Mobile: sidebar hidden, hamburger to open overlay
   - Desktop: sidebar inline, collapsible

2. **Update `useResponsive` breakpoints**:
   ```typescript
   // Current: isSmallScreen = isMobile || isTablet (both get same treatment)
   // New: keep isSmallScreen but add isTabletUp for sidebar icon-rail
   isTabletUp: isTablet || isDesktop,  // 768px+ gets icon rail
   ```

3. **Content area responsive adjustments:**
   - Project page tree: full panel on desktop, collapsible on tablet
   - Issue board view: horizontal scroll on tablet, full grid on desktop
   - Page editor: full-width on tablet (margin panel collapses)

## Recommended Project Structure (New/Modified Files)

```
backend/
  alembic/versions/
    062_add_page_tree_columns.py          # NEW: parent_id, depth, position on notes
  src/pilot_space/
    api/v1/
      routers/
        workspace_notes.py                # MODIFY: add tree endpoints
      schemas/
        note.py                           # MODIFY: add parent_id, depth, position, children
        page_tree.py                      # NEW: tree-specific request/response schemas
    infrastructure/database/
      models/
        note.py                           # MODIFY: add parent_id, depth, position, relationships
      repositories/
        note_repository.py                # MODIFY: add tree queries (get_tree, move_page)
    application/services/
      note/
        page_tree_service.py              # NEW: tree operations with depth validation

frontend/
  src/
    stores/features/projects/
      ProjectTreeStore.ts                 # NEW: MobX store for page trees
    features/projects/
      components/
        page-tree/
          page-tree.tsx                   # NEW: recursive tree component
          page-tree-item.tsx              # NEW: single tree node with indent
          page-tree-actions.tsx           # NEW: context menu (rename, move, delete)
        issue-views/
          issue-view-tabs.tsx             # NEW: tab container (Board/List/Timeline/Priority)
          issue-board-view.tsx            # NEW: kanban board (grouped by state)
          issue-list-view.tsx             # NEW: table/list view
          issue-timeline-view.tsx         # NEW: gantt-style timeline
          issue-priority-view.tsx         # NEW: grouped by priority
      hooks/
        usePageTree.ts                    # NEW: TanStack Query hook for tree data
        useMovePage.ts                    # NEW: mutation for reparenting/reordering
    components/layout/
      sidebar.tsx                         # MODIFY: add project trees, extract sub-components
      sidebar-project-tree.tsx            # NEW: project tree section
      sidebar-shortcuts.tsx              # NEW: extracted Pinned/Recent from sidebar.tsx
      app-shell.tsx                       # MODIFY: tablet-specific sidebar behavior
    hooks/
      useMediaQuery.ts                    # MODIFY: add isTabletUp convenience
    types/
      note.ts                            # MODIFY: add parentId, depth, position, children
```

### Structure Rationale

- **`page-tree/` under `features/projects/`**: Page trees live within projects, so they belong in the projects feature module. Personal pages reuse the same tree component but render in the notes context.
- **`issue-views/` under `features/projects/`**: Issue database views are a project-hub concern, not a standalone issue feature. They import issue components but live under projects.
- **`sidebar-project-tree.tsx` and `sidebar-shortcuts.tsx`**: Extracting from `sidebar.tsx` (currently 671 lines) prevents exceeding the 700-line limit and improves maintainability.
- **`ProjectTreeStore` in global stores**: Tree expansion state must persist across page navigations (sidebar is always mounted in `AppShell`), so it lives in the global store, not in a feature-local store.

## Data Flow

### Page Tree Load Flow

```
Sidebar mounts
    |
    v
ProjectTreeStore.loadTrees(projectIds[])
    |
    v
TanStack Query: GET /workspaces/{wid}/pages/tree?project_ids=...
    |
    v
Backend: NoteRepository.get_project_trees(project_ids)
  -> SELECT id, title, parent_id, depth, position, project_id
     FROM notes
     WHERE project_id IN (:pids) AND is_deleted = false
     ORDER BY depth, position
    |
    v
Frontend: Build TreeNode[] hierarchy from flat list
    |
    v
ProjectTreeStore.trees.set(projectId, rootNodes)
    |
    v
SidebarProjectTree renders recursively
```

### Page Move Flow (Drag & Drop / Indent)

```
User drags page B under page A
    |
    v
ProjectTreeStore.movePage(pageId, newParentId, newPosition)
    |
    v
Optimistic: update trees map immediately
    |
    v
PATCH /workspaces/{wid}/notes/{noteId}
  body: { parent_id: newParentId, position: newPosition }
    |
    v
Backend: PageTreeService.move_page()
  1. Validate depth <= 2 (new parent depth + 1)
  2. Validate children won't exceed depth 2 (recursive check)
  3. Update note.parent_id, note.depth, note.position
  4. Cascade depth update to all descendants
    |
    v
On success: TanStack invalidates tree query
On error: ProjectTreeStore rolls back optimistic update
```

### Embedded Issue Views Data Flow

```
Project Hub Page renders IssueViewTabs
    |
    v
Active tab (e.g., Board) fetches:
  TanStack Query: GET /workspaces/{wid}/projects/{pid}/issues?state_group=...
    |
    v
Board view groups issues by state, renders columns
    |
    v
Issue card click: router.push(`/{ws}/issues/{issueId}`)
  (navigates to existing issue detail page)
```

## Backend API Changes

### New Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/workspaces/{wid}/pages/tree` | Batch tree fetch for sidebar (query param: `project_ids`) |
| `PATCH` | `/workspaces/{wid}/notes/{nid}/move` | Move page (parent_id, position) with depth validation |

### Modified Endpoints

| Method | Path | Change |
|--------|------|--------|
| `GET` | `/workspaces/{wid}/notes` | Add `owner_only=true` query param for personal pages |
| `POST` | `/workspaces/{wid}/notes` | Accept `parent_id` in create body |
| `GET` | `/workspaces/{wid}/notes/{nid}` | Response includes `parentId`, `depth`, `children[]` |

### No Changes Needed

| Method | Path | Why |
|--------|------|-----|
| `GET` | `/workspaces/{wid}/projects/{pid}/issues` | Already supports filtering/sorting for all four views |
| All issue CRUD | Various | Issues are project-scoped already |

## Anti-Patterns

### Anti-Pattern 1: Recursive SQL Queries for Tree Loading

**What people do:** Use recursive CTEs or multiple round-trips to load tree nodes level by level.
**Why it is wrong:** For a max-depth-2 tree, recursion is unnecessary overhead. A flat query with `ORDER BY depth, position` and client-side tree building is simpler and faster.
**Do this instead:** Single flat query, build tree client-side:

```typescript
function buildTree(flatNodes: FlatNode[]): TreeNode[] {
  const map = new Map<string, TreeNode>();
  const roots: TreeNode[] = [];
  for (const node of flatNodes) {
    map.set(node.id, { ...node, children: [] });
  }
  for (const node of flatNodes) {
    const treeNode = map.get(node.id)!;
    if (node.parentId) {
      map.get(node.parentId)?.children.push(treeNode);
    } else {
      roots.push(treeNode);
    }
  }
  return roots;
}
```

### Anti-Pattern 2: Storing Expanded Tree State in Backend

**What people do:** Persist tree expand/collapse state in the database via user preferences.
**Why it is wrong:** Creates unnecessary API calls on every toggle. Expand state is ephemeral UI preference.
**Do this instead:** Use `localStorage` with `pilot-space:tree-expanded:{workspaceId}` key. The `ProjectTreeStore` hydrates from localStorage on mount, just like `UIStore` does.

### Anti-Pattern 3: Separate Tables for "Pages" vs "Notes"

**What people do:** Create a new `pages` table to represent the tree structure, keeping `notes` for flat documents.
**Why it is wrong:** A "page" IS a note with tree metadata. Splitting creates data duplication, broken links, and two sets of CRUD endpoints. The existing Note model already has `project_id`, `owner_id`, `content`, and all the TipTap integration.
**Do this instead:** Add `parent_id`, `depth`, `position` columns directly to the `notes` table. A page is a note. A personal page is a note with `project_id IS NULL`. Terminology can differ in the UI while sharing the same data model.

### Anti-Pattern 4: Fetching Full Issue Data for Sidebar Tree

**What people do:** Load all issues to show counts or status in the sidebar project tree.
**Why it is wrong:** Sidebar should be lightweight. Loading all issues for every project on every page load is expensive.
**Do this instead:** The sidebar tree shows only pages (notes), not issues. Issue counts per project come from the existing `Project.issueCount` and `Project.openIssueCount` fields already on the `useProjects` query.

### Anti-Pattern 5: MobX Observer on TipTap Editor Content Component

**What people do:** Wrap the page editor content in `observer()` to make it reactive.
**Why it is wrong:** This causes nested `flushSync` errors in React 19 with TipTap's `ReactNodeViewRenderer`. This is a known constraint documented in `.claude/rules/tiptap.md`.
**Do this instead:** Use the Context Bridge pattern (existing `IssueNoteContext`). The page editor content component stays a plain React component; data flows via context from an observer parent.

## Integration Points

### Internal Boundaries

| Boundary | Communication | Integration Notes |
|----------|---------------|-------------------|
| Sidebar <-> ProjectTreeStore | MobX observable | Sidebar reads `trees` and `expandedNodes` observables |
| ProjectTreeStore <-> API | TanStack Query + MobX | TanStack fetches, MobX manages UI state (expanded, dragging) |
| Page Tree <-> Note Editor | Next.js routing | Clicking a tree node navigates to `/{ws}/notes/{noteId}` |
| Issue Views <-> Existing Issue Hooks | Shared TanStack Query keys | Issue views use existing `useIssues` hooks with project filter |
| NoteStore <-> Page Tree | Shared note data | NoteStore gains `parentId`/`depth` on Note type; tree store is separate |
| Knowledge Graph pipeline | Background job | `kg_populate_handler.py` already processes notes -- no change needed |

### External Services

| Service | Impact | Notes |
|---------|--------|-------|
| Meilisearch | None | Note search index unchanged; `parentId` can be added to index later if needed |
| Supabase Auth/RLS | None | Notes RLS policies already filter by workspace_id; parent_id is within same workspace |
| AI Ghost Text | None | Ghost text operates on note content regardless of tree position |
| pgmq Queue | None | KG populate job works on individual notes; tree structure is irrelevant to processing |

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-100 projects, <1000 pages per workspace | Current approach is fine. Single flat query for tree. |
| 100-500 projects | Lazy-load trees per project on sidebar expand (not all at once). Already supported by `loadTree(projectId)`. |
| 1000+ pages in a single project | Paginate children at depth 0; show "Load more" for large root lists. Depth 1-2 children are bounded by parent. |

### First Bottleneck: Sidebar Tree Load

With many projects, loading all trees on sidebar mount is wasteful. Mitigate by:
1. Only load trees for projects whose nodes are expanded (check localStorage)
2. Load remaining trees lazily when user expands a project
3. The batch endpoint `GET /pages/tree?project_ids=...` supports selective loading

### Second Bottleneck: Issue View Rendering

Board view with hundreds of issues per state column. Mitigate by:
1. Virtual scrolling within columns (already using `@tanstack/react-virtual` in notes page)
2. Pagination per state group

## Suggested Build Order

Build order is dependency-driven to ensure each phase has testable output:

| Order | Component | Depends On | Rationale |
|-------|-----------|------------|-----------|
| 1 | DB migration (parent_id, depth, position) | Nothing | Foundation for all tree features |
| 2 | Backend tree API (get_tree, move, create with parent) | Migration | Backend must exist before frontend |
| 3 | Note type updates (frontend types + API client) | Backend API | Types drive all frontend components |
| 4 | ProjectTreeStore (MobX) | Frontend types | Store drives all tree UI |
| 5 | Page tree component | ProjectTreeStore | Reusable tree renderer |
| 6 | Sidebar integration (SidebarProjectTree) | Page tree component | Highest user-visible impact |
| 7 | Project hub page with tree panel | Page tree component | Project-centric hub |
| 8 | Embedded issue views (Board, List) | Project hub page | Core issue views first |
| 9 | Embedded issue views (Timeline, Priority) | Board/List views | Lower priority views |
| 10 | Personal pages (Notes page refactor) | Tree component | Reuse tree for personal pages |
| 11 | Responsive layout refinements | All above | Polish responsive behavior |
| 12 | Visual design refresh | All above | Typography, spacing, colors applied holistically |

**Critical path:** 1 -> 2 -> 3 -> 4 -> 5 -> 6 (sidebar tree is the highest-impact deliverable).

**Parallelizable:** Steps 7-10 can be built in parallel by different developers once step 5 is complete. Step 8-9 (issue views) can run in parallel with step 10 (personal pages).

## Sources

- Existing codebase analysis (HIGH confidence -- direct code inspection):
  - `backend/src/pilot_space/infrastructure/database/models/note.py` -- Note model with project_id, owner_id
  - `backend/src/pilot_space/infrastructure/database/models/project.py` -- Project model
  - `backend/src/pilot_space/infrastructure/database/models/issue.py` -- Issue model with start_date, target_date
  - `frontend/src/components/layout/sidebar.tsx` -- Current sidebar (671 lines, flat nav)
  - `frontend/src/components/layout/app-shell.tsx` -- Current responsive layout
  - `frontend/src/hooks/useMediaQuery.ts` -- Existing responsive hooks
  - `frontend/src/stores/UIStore.ts` -- UIStore with sidebar persistence
  - `frontend/src/stores/features/notes/NoteStore.ts` -- NoteStore pattern
  - `frontend/src/types/note.ts` -- Note type definition
  - `.claude/rules/tiptap.md` -- TipTap observer constraint
  - `.planning/PROJECT.md` -- Milestone requirements

---
*Architecture research for: Notion-style page tree integration with existing Pilot Space codebase*
*Researched: 2026-03-12*

# Feature Research

**Domain:** Notion-style page tree, project-centric navigation, embedded database views, visual design refresh, responsive layout
**Researched:** 2026-03-12
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist in a Notion-style restructure. Missing these means the new model feels broken or half-baked.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Nested page tree in sidebar (3 levels) | Core Notion mental model; users expect to expand/collapse child pages in a tree structure | HIGH | Requires new `parent_id` self-referential FK on notes/pages, `position` ordering field, recursive tree query. Existing Note model has `project_id` but no `parent_id`. Must add tree loading API endpoint returning nested structure. |
| Expand/collapse toggles on tree nodes | Notion users instinctively click triangles to drill into sub-pages; accordion-style is table stakes | LOW | Pure frontend state per-node. Persist expanded state in localStorage keyed by user+workspace. |
| Inline page creation from sidebar | Hovering a page shows "+" to create child page nested inside it; Notion's primary creation flow | MEDIUM | Requires API: `POST /pages` with `parent_id`. Frontend: inline input field that appears on hover of tree node, auto-focuses, creates on Enter. |
| Breadcrumb navigation showing page hierarchy | Users need to understand where they are in the tree; every Notion-like tool has this | LOW | Derive from parent chain. Existing header area can host breadcrumbs. Query parent chain on page load (max 3 levels, so max 3 breadcrumb segments). |
| Drag-and-drop reordering in sidebar tree | Notion users expect to drag pages to reorder and re-parent them within the tree | HIGH | Use `@dnd-kit/sortable` (already likely in the codebase for Kanban) or `react-complex-tree`. Must handle re-parenting (change `parent_id`) + reordering (change `position`). Optimistic updates essential for feel. |
| Project as hub with expandable page tree | Project sidebar item expands to show its page tree; this is the core navigation restructure | HIGH | Replace current flat "Notes" sidebar section with per-project expandable trees. Project items in sidebar become tree roots. Requires lazy-loading children on expand. |
| Embedded issue database views in pages | Users expect to see project issues as Board/List/Table inline within a project page, like Notion's inline databases | HIGH | Reuse existing `BoardView`, `ListView`, `TableView` components from `features/issues/components/views/`. Wrap them in an embeddable container that can live inside a page or a dedicated project tab. Need view switcher toolbar. |
| Two ownership models: project pages + personal pages | Milestone spec requires removing workspace-level notes; "Notes" nav shows personal pages, projects show project pages | MEDIUM | Add `ownership_type` enum (`project`, `personal`) to page model. Personal pages have `owner_id` set, no `project_id`. Project pages have `project_id` set. Filter accordingly in each context. Migration to reclassify existing notes. |
| View switcher for issue database (Board/List/Table) | Users expect to toggle between views on embedded issue databases, matching existing top-level issue views | MEDIUM | Toolbar component with segmented control (Board | List | Table). Already have all three view components. Wire view preference per project (stored in project settings JSON or localStorage). |
| Page icons (emoji picker) | Every Notion page has an emoji icon shown in sidebar tree and page header; expected visual feature | LOW | Add `icon` field to page model (already exists on Project as `icon: String(50)`). Use emoji picker component (many lightweight React options). Display in sidebar tree nodes and page header. |
| Page title inline editing | Click page title to edit inline, like Notion; no separate edit mode | LOW | Existing TipTap editor already handles title as first block. Ensure sidebar tree reflects title changes in real-time via MobX store update. |

### Differentiators (Competitive Advantage)

Features that set Pilot Space apart from vanilla Notion clones. Aligned with AI-augmented SDLC core value.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| AI ghost text in page tree context | Ghost text completions are context-aware of the page's position in the tree hierarchy and sibling pages | MEDIUM | Existing ghost text infrastructure. Enhancement: pass parent page title + sibling titles as context to the ghost text prompt. Requires minor AI prompt changes, not new infrastructure. |
| Issue extraction scoped to project | When extracting issues from a note, auto-assign to the note's parent project | LOW | Existing extraction pipeline. Add `project_id` from page context to extraction output. Trivial enhancement. |
| Priority view for embedded database | Group issues by priority with swimlanes (Urgent/High/Medium/Low/None) -- not standard in Notion | MEDIUM | New view variant alongside Board/List/Table. Reuse Board component with `priority` as grouping property instead of `state`. |
| Timeline/Gantt view for project issues | Visualize issue timelines within a project; Linear-like differentiator | HIGH | New component. Requires `start_date`/`due_date` on issues (may already exist). Horizontal scrolling timeline with draggable bars. Consider `@bryntum/gantt` or custom with CSS grid. Defer to later phase if scope is tight. |
| Quick-switcher enhanced with tree awareness | Cmd+K palette shows page hierarchy path (e.g., "Project > Design > Colors") | LOW | Existing CommandPalette. Enhance search results to show breadcrumb path alongside page title. Requires tree path in search index. |
| Keyboard navigation in sidebar tree | Arrow keys to navigate tree, Enter to open, Tab to expand/collapse | MEDIUM | Accessibility benefit. Implement `aria-tree` role with `aria-treeitem` children. Arrow key handlers for tree traversal. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Unlimited nesting depth | "Notion does it" | Notion's infinite nesting is a well-known organizational trap; users create 8+ level trees that become unmaintainable. Deep trees cause sidebar scroll hell, slow recursive queries, complex drag-drop edge cases. | Cap at 3 levels (project root > section > leaf page). Covers 95% of use cases. Enforced in API. |
| Real-time collaborative page tree editing | Multiple users reordering tree simultaneously | Requires CRDT/OT for tree structure (not just document content). Conflict resolution for move operations is notoriously hard. Y.js handles doc content but tree structure sync is separate problem. | Single-writer tree mutations with optimistic UI. Refresh tree on navigation. Collaborative editing of page *content* (via existing Y.js infra) is separate from tree structure. |
| Full database-in-page (Notion-style inline DB creation) | Users want to create arbitrary databases inside any page | Massive scope: schema builder, property type system, formula engine, relation/rollup properties. This is essentially building Notion's database engine. | Embed *existing* issue views into pages. Issues are the database. Don't build a generic database engine. |
| Page-level permissions (per-page ACL) | "I want to share this page but not that page" | Enormous complexity: per-page RLS policies, inheritance rules, sharing UI, permission checks on every tree traversal. Breaks the simple workspace RBAC model. | Use project-level access (existing RBAC). Personal pages are owner-only by default. Project pages inherit project membership. |
| Mobile-first responsive design | "Works on my phone" | Developer workflows are desktop-primary. Mobile layout for nested trees is terrible UX (deep indentation on 375px screen). Milestone explicitly excludes mobile. | Desktop (1280px+) and tablet (768-1024px) only. Tablet gets collapsed sidebar + full content area. Mobile gets a "use desktop" message or minimal read-only view. |
| Custom page templates in tree | "Let me create a template that auto-populates child pages" | Template system for tree structures is complex: recursive template instantiation, placeholder substitution, partial application. | Offer flat page templates (existing `TemplatePicker`). User creates child pages manually after using a template for the root page. |
| Synced blocks / transclusion | Reference the same content block across multiple pages | Requires block-level identity, reference tracking, update propagation. TipTap doesn't natively support this. Major architectural addition. | Use note-to-note links (existing `NoteNoteLink` model) to reference related content. Show link previews inline. |

## Feature Dependencies

```
[Page Model with parent_id + position]
    |
    +--requires--> [Tree API (CRUD + reorder)]
    |                  |
    |                  +--requires--> [Sidebar Page Tree Component]
    |                  |                  |
    |                  |                  +--requires--> [Drag-and-Drop in Tree]
    |                  |                  |
    |                  |                  +--requires--> [Expand/Collapse State]
    |                  |
    |                  +--requires--> [Breadcrumb Navigation]
    |
    +--requires--> [Ownership Model Migration (project vs personal)]

[Embedded Issue Database Views]
    |
    +--requires--> [Project Hub Navigation] (project page as container)
    |
    +--reuses--> [Existing BoardView, ListView, TableView]
    |
    +--requires--> [View Switcher Toolbar]

[Visual Design Refresh]
    |
    +--independent--> (Can be done in parallel with structural changes)
    |
    +--touches--> [Sidebar styling, page header, typography, spacing, colors]

[Responsive Layout]
    |
    +--requires--> [Visual Design Refresh] (responsive is a layout concern)
    |
    +--reuses--> [Existing useResponsive hooks, AppShell breakpoints]
```

### Dependency Notes

- **Page Model requires migration first:** `parent_id`, `position`, `ownership_type` must exist before any tree UI work. This is the foundational change.
- **Sidebar Tree requires Tree API:** Cannot render tree without an endpoint returning nested page structure. API must support lazy-loading children for performance.
- **Embedded Views reuse existing components:** BoardView, ListView, TableView already exist. The work is embedding them in a project hub context with a view switcher, not rebuilding them.
- **Visual Design Refresh is independent:** Typography, spacing, colors, component polish can be done in parallel with structural backend/frontend changes. No data model dependency.
- **Responsive Layout builds on Visual Refresh:** Responsive breakpoint behavior depends on the refreshed component dimensions and spacing. Existing `useResponsive` hooks and `AppShell` breakpoints are reusable.
- **Drag-and-drop depends on tree rendering:** Must have working tree display before adding drag-drop interactions on top.

## MVP Definition

### Launch With (v1)

Minimum viable for the Notion-style restructure to feel complete and usable.

- [ ] **Page model with `parent_id` + `position` + `ownership_type`** -- foundational data model; everything depends on this
- [ ] **Tree CRUD API** -- create, read (nested), update (move/reorder), delete pages with tree semantics
- [ ] **Sidebar page tree per project** -- expand project to see its page tree (3 levels), expand/collapse toggles, inline "+" creation
- [ ] **Personal pages section** -- "Notes" nav shows current user's personal pages (flat or shallow tree)
- [ ] **Page breadcrumb navigation** -- show parent > child > current in page header
- [ ] **Embedded issue views in project hub** -- Board/List/Table views embedded in project page with view switcher
- [ ] **Ownership migration** -- migrate existing notes to project or personal ownership; remove workspace-level concept
- [ ] **Visual design refresh: typography + spacing + colors** -- Notion-like feel with Inter/system font, 8px grid, muted palette
- [ ] **Desktop + tablet responsive layout** -- sidebar collapses to icons on tablet; content area adapts

### Add After Validation (v1.x)

Features to add once the core tree and project hub are working and users are navigating successfully.

- [ ] **Drag-and-drop reordering in sidebar tree** -- adds polish but not essential for first usable version; complex interaction
- [ ] **Page emoji icons** -- nice visual polish, not blocking usability
- [ ] **Priority view for embedded database** -- additional view variant after Board/List/Table are embedded
- [ ] **Keyboard navigation in sidebar tree** -- accessibility improvement, add after tree is stable
- [ ] **Cmd+K tree-aware search** -- enhance search results with breadcrumb paths

### Future Consideration (v2+)

Features to defer until the restructure is validated and stable.

- [ ] **Timeline/Gantt view** -- high complexity, separate feature
- [ ] **AI ghost text tree context awareness** -- requires prompt engineering iteration
- [ ] **Page templates for tree nodes** -- wait for user demand signal
- [ ] **Cross-project page references** -- link pages across projects

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Page model + tree API | HIGH | HIGH | P1 |
| Sidebar page tree per project | HIGH | HIGH | P1 |
| Ownership model migration | HIGH | MEDIUM | P1 |
| Personal pages section | HIGH | LOW | P1 |
| Page breadcrumb navigation | HIGH | LOW | P1 |
| Embedded issue views in project hub | HIGH | MEDIUM | P1 |
| View switcher toolbar | MEDIUM | LOW | P1 |
| Visual design refresh (typography/spacing/colors) | HIGH | MEDIUM | P1 |
| Desktop + tablet responsive layout | HIGH | MEDIUM | P1 |
| Expand/collapse toggle persistence | MEDIUM | LOW | P1 |
| Drag-and-drop tree reordering | MEDIUM | HIGH | P2 |
| Page emoji icons | LOW | LOW | P2 |
| Inline page creation from sidebar hover | MEDIUM | MEDIUM | P2 |
| Priority view for embedded DB | MEDIUM | MEDIUM | P2 |
| Keyboard tree navigation | MEDIUM | MEDIUM | P2 |
| Cmd+K tree-aware search | LOW | LOW | P2 |
| Timeline/Gantt view | MEDIUM | HIGH | P3 |
| AI ghost text tree context | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch -- the restructure is incomplete without these
- P2: Should have, add in follow-up phases -- improves polish and usability
- P3: Nice to have, future consideration -- new capabilities, not part of restructure

## Competitor Feature Analysis

| Feature | Notion | Linear | Pilot Space Approach |
|---------|--------|--------|---------------------|
| Page nesting | Unlimited depth, drag to nest | No page tree (docs are flat) | 3-level max within projects. Opinionated constraint to prevent chaos. |
| Sidebar tree | Accordion with lazy-load children, hover "+" to create | Flat list of projects with sub-nav tabs (Issues, Cycles, etc.) | Hybrid: project-level accordion tree (Notion) with sub-nav tabs (Linear) for issues/cycles/settings |
| Embedded databases | Full inline DB with schema builder, any property types | No inline databases; issues and projects are separate views | Embed existing issue views (Board/List/Table) in project pages. No generic database engine. |
| Database view types | Table, Board, List, Calendar, Timeline, Gallery | Board, List, Triage | Board, List, Table (existing). Add Priority view. Timeline as P3. |
| Breadcrumbs | Full path shown in header with each segment clickable | Project > Section shown in header | Full tree path (max 3 segments) in header, clickable |
| Drag-and-drop in tree | Drag to reorder and re-parent | Drag to reorder issues in list | Drag to reorder + re-parent pages in sidebar tree |
| Personal vs shared | Shared teamspace pages + private pages section | No personal pages concept | Personal pages (user-owned) + project pages (team-owned) |
| Visual design | Clean, minimal, lots of whitespace, system fonts, 8px grid | Ultra-clean, monospace accents, purple accent, tight spacing | Notion-inspired: system fonts, generous whitespace, muted colors, 8px grid. Keep existing shadcn/ui foundation. |
| Responsive | Desktop-first, basic mobile app | Desktop-only web app | Desktop + tablet. Tablet: collapsed sidebar, adapted content. |
| Page icons | Emoji or uploaded icon per page | Emoji per project only | Emoji per page (P2), emoji per project (existing `icon` field) |

## Existing Assets to Reuse

These existing components and infrastructure directly support the new features:

| Existing Asset | Location | Reuse For |
|----------------|----------|-----------|
| BoardView | `features/issues/components/views/board/BoardView.tsx` | Embedded issue board in project hub |
| ListView | `features/issues/components/views/list/ListView.tsx` | Embedded issue list in project hub |
| TableView | `features/issues/components/views/table/TableView.tsx` | Embedded issue table in project hub |
| IssueToolbar + FilterBar | `features/issues/components/views/IssueToolbar.tsx` | View switcher and filters for embedded views |
| AppShell responsive layout | `components/layout/app-shell.tsx` | Sidebar collapse behavior on tablet (already works) |
| useResponsive hooks | `hooks/useMediaQuery.ts` | Breakpoint detection (sm/md/lg/xl already defined) |
| Sidebar component | `components/layout/sidebar.tsx` | Base for adding project tree sections (replace Pinned/Recent notes) |
| Note model with `project_id` | `infrastructure/database/models/note.py` | Already has project association; add `parent_id` + `position` |
| Project model with `icon` | `infrastructure/database/models/project.py` | Project already supports emoji icons |
| NoteStore (MobX) | `stores/` | Extend or create PageStore for tree state management |
| TipTap editor infrastructure | `features/notes/editor/` | Reuse for page content editing (pages are notes with tree structure) |
| CommandPalette | `components/search/CommandPalette.tsx` | Enhance with tree-aware search results |

## Sources

- [Notion Help Center - Navigate with the sidebar](https://www.notion.com/help/navigate-with-the-sidebar)
- [Notion Help Center - Intro to databases](https://www.notion.com/help/intro-to-databases)
- [Notion Help Center - Board view](https://www.notion.com/help/boards)
- [Notion Help Center - Table view](https://www.notion.com/help/tables)
- [Notion Help Center - Views, filters, sorts & groups](https://www.notion.com/help/views-filters-and-sorts)
- [Notion Colors: All Hex Codes](https://matthiasfrank.de/en/notion-colors/)
- [UI Breakdown of Notion's Sidebar](https://medium.com/@quickmasum/ui-breakdown-of-notions-sidebar-2121364ec78d)
- [React Complex Tree - Drag and Drop](https://rct.lukasbach.com/docs/guides/drag-and-drop/)
- [react-notion-sortable-tree](https://github.com/suimenkathemove/react-notion-sortable-tree)
- [Managing Infinite Nesting with Notion Nested Pages](https://ones.com/blog/manage-infinite-nesting-notion-nested-pages/)

---
*Feature research for: Notion-style page tree, project-centric navigation, embedded database views, visual design refresh, responsive layout*
*Researched: 2026-03-12*

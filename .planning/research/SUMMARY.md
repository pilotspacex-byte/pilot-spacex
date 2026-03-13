# Project Research Summary

**Project:** Pilot Space v1.0.0-alpha2 — Notion-Style Restructure
**Domain:** SDLC platform UI restructure — nested page tree, project-centric navigation, embedded issue views, visual design refresh, responsive layout
**Researched:** 2026-03-12
**Confidence:** HIGH

## Executive Summary

This milestone restructures Pilot Space's navigation from a flat note list to a Notion-style 3-level page tree organized around projects, with embedded issue database views, a visual design refresh, and desktop/tablet responsive layout. The critical finding across all research is that **the existing stack already contains every library needed** — no new npm packages or Python packages are required. The work is schema evolution (adding `parent_id`, `depth`, `position` to the existing `notes` table), component extraction and extension (sidebar tree, editor decoupling, issue view embedding), and CSS token refinement.

The recommended approach is an adjacency list (`parent_id` self-referential FK) on the existing `notes` table with a hard depth cap of 3 levels enforced via DB CHECK constraint. The frontend extends the existing `@dnd-kit/sortable` for tree drag-and-drop, adds a new `ProjectTreeStore` (MobX) for tree UI state, and reuses existing `BoardView`/`ListView`/`TableView` components for embedded issue database views in the project hub. The two ownership models (project pages vs personal pages) require no new table — the distinction is `project_id IS NOT NULL` vs `project_id IS NULL` with `owner_id` filtering, but RLS policies must be updated atomically with the schema migration.

The top risks are: (1) the flat-to-tree migration silently breaking existing note references, RLS policies, and knowledge graph nodes if ownership semantics change without coordinated policy updates; (2) TipTap's property block extension crashing on non-issue pages because the guard plugins assume issue context; and (3) the visual design refresh cascading unintended style changes across the 880K-line codebase via global CSS variable mutations. All three are avoidable with the phased approach detailed below.

## Key Findings

### Recommended Stack

No new libraries. The entire feature set builds on the existing stack: Next.js 16.1, React 19.2, MobX 6, TanStack Query 5, shadcn/ui, TipTap 3, Tailwind CSS 4, @dnd-kit (core + sortable), react-resizable-panels, Motion, PostgreSQL 16, SQLAlchemy async, FastAPI. See `.planning/research/STACK.md` for full analysis.

**Core technology decisions:**
- **Adjacency list (parent_id + position + depth)** on `notes` table — simplest tree model for max 3 levels; re-parenting is a single UPDATE; no ltree extension needed
- **@dnd-kit/sortable (existing)** for tree drag-and-drop — already powers OutlineTree.tsx; extending with indentation logic is ~100 lines, not a new dependency
- **MobX ProjectTreeStore (new store)** for tree UI state — expand/collapse, drag state, optimistic updates; persisted to localStorage; separate from existing NoteStore
- **Flat query + client-side tree build** — single `SELECT ... ORDER BY depth, position` returns all nodes; client builds hierarchy; no recursive CTE needed for reads at this depth
- **CSS custom property refinement** in `globals.css` — Notion-like typography, spacing, colors via token changes, not library additions

### Expected Features

See `.planning/research/FEATURES.md` for full prioritization matrix and competitor analysis.

**Must have (P1 — launch is incomplete without these):**
- Page model with `parent_id` + `position` + ownership classification
- Tree CRUD API (create, read nested, move/reorder, delete with cascade)
- Sidebar page tree per project (3 levels, expand/collapse, inline "+" creation)
- Personal pages section (replacing workspace-level notes concept)
- Page breadcrumb navigation (parent > child > current)
- Embedded issue views in project hub (Board/List/Table with view switcher)
- Ownership migration (classify existing notes as project or personal)
- Visual design refresh (typography, spacing, colors)
- Desktop + tablet responsive layout

**Should have (P2 — add after core is stable):**
- Drag-and-drop reordering in sidebar tree
- Page emoji icons
- Priority view for embedded database
- Keyboard tree navigation (accessibility)
- Cmd+K tree-aware search

**Defer (v2+):**
- Timeline/Gantt view (high complexity, separate feature)
- AI ghost text tree context awareness (prompt engineering iteration)
- Page templates for tree nodes
- Cross-project page references

### Architecture Approach

The architecture extends the existing 5-layer clean architecture without new layers. The `notes` table gains three columns (`parent_id`, `depth`, `position`). The frontend adds a `ProjectTreeStore` and `SidebarProjectTree` component, extracts a base `PageEditor` from the issue-coupled `IssueEditorContent`, and embeds existing issue view components in a new project hub layout. See `.planning/research/ARCHITECTURE.md` for component boundaries and data flows.

**Major components:**
1. **Note model extension** — `parent_id` (self-referential FK), `depth` (0-2, CHECK constrained), `position` (fractional indexing for insert-between)
2. **ProjectTreeStore (MobX)** — manages per-project tree state, expanded nodes (Set), drag state; persists to localStorage; loads lazily per-project
3. **SidebarProjectTree** — extracted from sidebar.tsx; renders collapsible per-project trees replacing flat Pinned/Recent sections
4. **PageEditor (base)** — extracted from issue editor; shared TipTap extensions without property block; issue editor layers property block on top
5. **IssueViewTabs** — tab container embedding existing Board/List/Table views inside project hub, fetching via TanStack Query with `projectId` prop
6. **Responsive layout refinement** — new `isTabletLayout` check added to `useResponsive()` without changing existing `isSmallScreen` semantics

### Critical Pitfalls

See `.planning/research/PITFALLS.md` for all 8 pitfalls with recovery strategies.

1. **Flat-to-tree migration breaks note references** — Add columns and RLS policies atomically in one migration; classify existing notes without removing any columns; run against staging data clone first. Phase 1 blocker.
2. **TipTap property block crashes on non-issue pages** — Extract base PageEditor without property block extension; issue editor layers it on top. Do NOT make property block "optional" within the same instance. Phase 3.
3. **RLS policy gaps expose personal pages** — SELECT policy must be `(project_page AND workspace_member) OR (personal_page AND owner_id match)`. Write policy in same migration as schema. Test with real PostgreSQL. Phase 1 blocker.
4. **Sidebar state explosion** — Dedicated ProjectTreeStore with `observable.shallow`; persist expanded state in localStorage; lazy-load trees per-project. Never put tree state in UIStore or NoteStore. Phase 4.
5. **Visual design refresh cascading breakage** — Change CSS tokens first, audit every page visually, do NOT change component-level classes simultaneously. Use new custom properties for tree-specific values. Phase 5.

## Implications for Roadmap

Based on research, suggested phase structure (6 phases):

### Phase 1: Data Model and Migration
**Rationale:** Every feature depends on `parent_id`, `depth`, `position` on the notes table. RLS policies must update atomically. This is the foundation.
**Delivers:** Updated notes schema with tree columns, ownership classification of existing notes, updated RLS policies for personal vs project pages, CHECK constraint on depth.
**Addresses:** Page model, ownership migration, data integrity.
**Avoids:** Pitfall 1 (migration breaks references), Pitfall 8 (RLS gaps).
**Estimated scope:** 1 migration file, model update, repository tree queries, integration tests with real PostgreSQL.

### Phase 2: Backend Tree API
**Rationale:** Frontend tree components need API endpoints before any UI work. Batch tree fetch, move endpoint with depth validation, create-with-parent.
**Delivers:** `GET /pages/tree` (batch), `PATCH /notes/{id}/move`, updated `POST /notes` and `GET /notes` with tree fields, `PageTreeService` with depth enforcement.
**Addresses:** Tree CRUD API, personal pages filtering (`owner_only` param).
**Avoids:** Pitfall 2 (N+1 queries — use flat query + client tree build, not recursive CTE).
**Estimated scope:** 2 new endpoints, 3 modified endpoints, 1 new service, repository methods, unit + integration tests.

### Phase 3: Editor Decoupling
**Rationale:** The TipTap editor is coupled to issue-specific property blocks. Project pages and personal pages need an editor without property block guards. Must decouple before building page tree UI that opens different page types.
**Delivers:** Base `PageEditor` component (shared extensions, no property block), issue editor as `PageEditor + PropertyBlockExtension`, simpler `PageContext` for non-issue pages.
**Addresses:** TipTap reuse across page types.
**Avoids:** Pitfall 3 (property block crashes on non-issue pages).
**Estimated scope:** Extract/refactor ~4-5 editor components, update page routes, verify ghost text + slash commands work on both page types.

### Phase 4: Sidebar Tree and Project Hub
**Rationale:** Highest user-visible impact. Depends on API (Phase 2) and editor (Phase 3). Combines sidebar restructure with project hub because they share `ProjectTreeStore` and tree components.
**Delivers:** `ProjectTreeStore` (MobX), `SidebarProjectTree` component, page tree component (recursive with expand/collapse), project hub page with tree panel + embedded issue views (Board/List/Table), personal pages section in Notes nav, breadcrumb navigation.
**Addresses:** Sidebar page tree, embedded issue views, personal pages, breadcrumbs, inline page creation, view switcher.
**Avoids:** Pitfall 4 (sidebar state explosion — dedicated store), Pitfall 7 (circular deps — issue views fetch via TanStack Query, not MobX store imports).
**Estimated scope:** Largest phase. ~15 new/modified frontend components, 1 new MobX store, sidebar extraction (keep under 700 lines).

### Phase 5: Visual Design Refresh
**Rationale:** Must happen AFTER structural UI changes are complete. Applying design tokens before the tree/hub UI exists means double work. Applying after means one consistent pass.
**Delivers:** Updated CSS custom properties (typography, spacing, colors, borders), Notion-like visual feel, dark mode parity, TipTap editor styling alignment.
**Addresses:** Visual design refresh (typography, spacing, colors).
**Avoids:** Pitfall 5 (cascading breakage — token changes first, then audit, then component-level tweaks).
**Estimated scope:** globals.css token updates, per-page visual audit, editor CSS alignment. Mostly CSS, minimal JS.

### Phase 6: Responsive Layout and Polish
**Rationale:** Responsive behavior depends on the final component dimensions from Phase 5. This is the polish pass. Also includes drag-and-drop tree reordering (P2 feature) since layout must be stable first.
**Delivers:** Tablet-specific sidebar behavior (icon rail at 768px, not mobile overlay), content area responsive adjustments, drag-and-drop tree reordering, breakpoint-specific testing.
**Addresses:** Desktop + tablet responsive layout, drag-and-drop reordering (P2).
**Avoids:** Pitfall 6 (responsive conflicts — add `isTabletLayout` without changing `isSmallScreen`).
**Estimated scope:** useResponsive hook extension, AppShell tablet behavior, content area responsive tweaks, drag-and-drop tree integration.

### Phase Ordering Rationale

- **Phases 1-2 are strictly sequential:** Schema must exist before API, API must exist before frontend.
- **Phase 3 before Phase 4:** Editor decoupling is a prerequisite for the project hub page which opens non-issue pages. Building the hub first and then trying to fix the editor creates rework.
- **Phase 4 is the critical delivery:** It produces the user-facing restructure. Everything before it is foundational; everything after is refinement.
- **Phase 5 after Phase 4:** Design tokens applied to finalized component structure, not a moving target.
- **Phase 6 last:** Responsive behavior calibrated against final layouts and design tokens.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Editor Decoupling):** TipTap extension extraction is codebase-specific; needs careful analysis of which extensions are shared vs issue-only. The `flushSync` constraint adds risk.
- **Phase 4 (Sidebar Tree + Project Hub):** Largest phase with the most new components. Drag-and-drop nesting with @dnd-kit needs prototyping — the indentation-based drop detection is not trivially documented.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Data Model):** Standard adjacency list migration. Well-documented SQLAlchemy self-referential pattern.
- **Phase 2 (Backend API):** Standard CRUD + tree query endpoints. No novel patterns.
- **Phase 5 (Visual Design):** CSS token changes. Standard Tailwind/shadcn approach.
- **Phase 6 (Responsive):** Standard responsive layout work. Existing hooks cover most needs.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No new libraries needed; all existing packages verified compatible. Decision is straightforward. |
| Features | HIGH | Clear P1/P2/P3 prioritization; anti-features well-identified; competitor analysis validates scope. |
| Architecture | HIGH | Based on direct codebase inspection of existing models, stores, components. Build order is dependency-driven. |
| Pitfalls | HIGH | All 8 pitfalls grounded in actual codebase constraints (TipTap rules, RLS rules, sidebar line count, responsive hooks). |

**Overall confidence:** HIGH

### Gaps to Address

- **Fractional indexing for position:** Architecture recommends `Numeric(10,4)` for insert-between ordering. Need to validate this works cleanly with @dnd-kit sort events or if integer reindexing is simpler. Resolve during Phase 1 planning.
- **Timeline/Gantt view feasibility:** Mentioned as P3 but the project hub tab structure assumes it exists. If deferred, the tab UI needs graceful degradation. Clarify during Phase 4 planning.
- **Knowledge graph impact:** `kg_populate_handler.py` processes notes; tree restructure may create empty "container" pages that should not generate NOTE_CHUNK nodes. Need a `page_type` check in the handler. Address during Phase 2.
- **Meilisearch index update:** Search results should show breadcrumb context after tree restructure. Not blocking but improves UX. Plan during Phase 4.
- **Existing notes migration UX:** Users seeing their flat notes reorganized into a tree. Need a "Migrated Notes" bucket or one-time notice. Design during Phase 4 planning.

## Sources

### Primary (HIGH confidence — direct codebase analysis)
- `backend/src/pilot_space/infrastructure/database/models/note.py` — current Note model schema
- `backend/src/pilot_space/infrastructure/database/models/project.py` — Project model with icon field
- `backend/src/pilot_space/infrastructure/database/models/issue.py` — Issue model with start_date, target_date
- `frontend/src/components/layout/sidebar.tsx` — current sidebar implementation (671 lines)
- `frontend/src/components/layout/app-shell.tsx` — responsive layout handling
- `frontend/src/hooks/useMediaQuery.ts` — existing breakpoint definitions
- `frontend/src/stores/UIStore.ts` — sidebar persistence pattern
- `.claude/rules/tiptap.md` — PropertyBlockNode constraints, flushSync issue
- `.claude/rules/rls-check.md` — RLS policy requirements
- `.claude/rules/migration.md` — migration immutability rules
- `.planning/PROJECT.md` — v1.0.0-alpha2 milestone requirements

### Secondary (MEDIUM confidence — library documentation and community patterns)
- [@dnd-kit sortable docs](https://docs.dndkit.com/presets/sortable) — nested sortable context support
- [PostgreSQL hierarchical data patterns](https://www.ackee.agency/blog/hierarchical-models-in-postgresql) — adjacency list vs ltree comparison
- [Notion Help Center](https://www.notion.com/help/navigate-with-the-sidebar) — sidebar navigation UX patterns
- [react-arborist](https://www.npmjs.com/package/react-arborist), [@headless-tree/react](https://www.npmjs.com/package/@headless-tree/react) — evaluated and rejected

### Tertiary (LOW confidence — needs validation)
- Fractional indexing with Numeric(10,4) — theoretical fit, needs practical validation with @dnd-kit
- Timeline/Gantt view with CSS grid — conceptual, deferred to v2+

---
*Research completed: 2026-03-12*
*Ready for roadmap: yes*

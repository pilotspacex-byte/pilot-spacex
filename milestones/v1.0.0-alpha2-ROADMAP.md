# Roadmap: Pilot Space

## Milestones

- ✅ **v1.0 Enterprise** — Phases 1–11 (shipped 2026-03-09)
- ✅ **v1.0-alpha Pre-Production Launch** — Phases 12–23 (shipped 2026-03-12)
- 🚧 **v1.0.0-alpha2 Notion-Style Restructure** — Phases 24–29 (in progress)

## Phases

<details>
<summary>✅ v1.0 Enterprise (Phases 1–11) — SHIPPED 2026-03-09</summary>

- [x] Phase 1: Identity & Access (9/9 plans) — completed 2026-03-07
- [x] Phase 2: Compliance & Audit (5/5 plans) — completed 2026-03-08
- [x] Phase 3: Multi-Tenant Isolation (8/8 plans) — completed 2026-03-08
- [x] Phase 4: AI Governance (10/10 plans) — completed 2026-03-08
- [x] Phase 5: Operational Readiness (7/7 plans) — completed 2026-03-09
- [x] Phase 6: Wire Rate Limiting + SCIM Token (1/1 plans) — completed 2026-03-09
- [x] Phase 7: Wire Storage Quota Enforcement (2/2 plans) — completed 2026-03-09
- [x] Phase 8: Fix SSO Integration (1/1 plans) — completed 2026-03-09
- [x] Phase 9: Login Audit Events (1/1 plans) — completed 2026-03-09
- [x] Phase 10: Wire Audit Trail (1/1 plans) — completed 2026-03-09
- [x] Phase 11: Fix Rate Limiting Architecture (1/1 plans) — completed 2026-03-09

Full archive: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.0-alpha Pre-Production Launch (Phases 12–23) — SHIPPED 2026-03-12</summary>

- [x] Phase 12: Onboarding & First-Run UX (3/3 plans) — completed 2026-03-09
- [x] Phase 13: AI Provider Registry + Model Selection (4/4 plans) — completed 2026-03-10
- [x] Phase 14: Remote MCP Server Management (4/4 plans) — completed 2026-03-10
- [x] Phase 15: Related Issues (3/3 plans) — completed 2026-03-10
- [x] Phase 16: Workspace Role Skills (4/4 plans) — completed 2026-03-10
- [x] Phase 17: Skill Action Buttons (2/2 plans) — completed 2026-03-11
- [x] Phase 18: Tech Debt Closure (3/3 plans) — completed 2026-03-11
- [x] Phase 19: Skill Registry & Plugin System (4/4 plans) — completed 2026-03-11
- [x] Phase 20: Skill Template Catalog (4/4 plans) — completed 2026-03-11
- [x] Phase 21: Documentation & Verification Closure (2/2 plans) — completed 2026-03-12
- [x] Phase 22: Integration Safety — Session & OAuth2 UI (2/2 plans) — completed 2026-03-12
- [x] Phase 23: Tech Debt Sweep (2/2 plans) — completed 2026-03-12

Full archive: `.planning/milestones/v1.0-alpha-ROADMAP.md`

</details>

### v1.0.0-alpha2 Notion-Style Restructure (In Progress)

**Milestone Goal:** Restructure Pilot Space from flat notes to a Notion-style project-centric model with nested page trees, embedded issue views, visual design refresh, and responsive layout for desktop and tablet.

- [x] **Phase 24: Page Tree Data Model** - Schema migration adding tree columns to notes table, ownership classification, and existing notes migration (completed 2026-03-12)
- [x] **Phase 25: Tree API & Page Service** - Backend endpoints for tree CRUD, move/re-parent, and sibling reordering with depth enforcement (completed 2026-03-12)
- [x] **Phase 26: Sidebar Tree & Navigation** - Project page tree in sidebar with expand/collapse, inline creation, personal pages section, breadcrumbs, and editor decoupling for non-issue pages (completed 2026-03-12)
- [x] **Phase 27: Project Hub & Issue Views** - Embedded Board/List/Table/Priority issue views in project page with view switcher and page emoji icons (completed 2026-03-12)
- [x] **Phase 28: Visual Design Refresh** - Notion-like typography, spacing, and color token update across the application (completed 2026-03-12)
- [x] **Phase 29: Responsive Layout & Drag-and-Drop** - Tablet sidebar collapse, content area adaptation, and drag-and-drop tree reordering (completed 2026-03-12)

## Phase Details

### Phase 24: Page Tree Data Model
**Goal**: Notes table supports hierarchical page trees with project and personal ownership
**Depends on**: Nothing (first phase of milestone)
**Requirements**: TREE-01, TREE-04, TREE-05
**Success Criteria** (what must be TRUE):
  1. User can create a page nested up to 3 levels within a project (parent_id, depth 0-2 enforced by DB CHECK constraint)
  2. User can create a personal page that is independent of any project (owner_id set, project_id NULL)
  3. Existing notes with project_id are classified as project pages; existing notes without project_id are classified as personal pages owned by their creator
  4. RLS policies enforce that personal pages are visible only to the owner and project pages are visible to workspace members
**Plans**: 2 plans

Plans:
- [ ] 24-01-PLAN.md — Note model tree columns, NoteFactory update, and unit tests
- [ ] 24-02-PLAN.md — Alembic migration 079: DDL + data migration + RLS policy replacement

### Phase 25: Tree API & Page Service
**Goal**: Users can move and reorder pages within the tree via API
**Depends on**: Phase 24
**Requirements**: TREE-02, TREE-03
**Success Criteria** (what must be TRUE):
  1. User can move a page to a different parent within the same project and the page's depth and children's depths are updated correctly
  2. User can reorder pages among siblings and the new position persists across page reloads
  3. Moving a page that would exceed the 3-level depth limit is rejected with a clear error
**Plans**: 2 plans

Plans:
- [ ] 25-01-PLAN.md — MovePageService, NoteRepository tree methods, schemas, DI wiring, and unit tests
- [ ] 25-02-PLAN.md — ReorderPageService and move/reorder API endpoints on workspace notes router

### Phase 26: Sidebar Tree & Navigation
**Goal**: Users navigate a project's nested page hierarchy from the sidebar and see their location via breadcrumbs
**Depends on**: Phase 25
**Requirements**: NAV-01, NAV-02, NAV-03, NAV-04
**Success Criteria** (what must be TRUE):
  1. User can expand a project in the sidebar to see its nested page tree (up to 3 levels) with expand/collapse toggles that persist across sessions
  2. User can click "+" on any tree node in the sidebar to create a new child page inline without leaving the current page
  3. User sees their personal pages listed under the "Notes" nav item in the sidebar
  4. User sees breadcrumb navigation (project > parent > child > current) in the page header and can click any breadcrumb to navigate
  5. Non-issue pages open in the editor without crashes (editor decoupled from issue-specific property block)
**Plans**: 3 plans

Plans:
- [ ] 26-01-PLAN.md — Backend parent_id support, frontend types, tree utilities, TanStack Query hooks, UIStore expand state
- [ ] 26-02-PLAN.md — ProjectPageTree and PersonalPagesList components, PageBreadcrumb component, sidebar wiring
- [ ] 26-03-PLAN.md — Wire PageBreadcrumb into note detail page, content sanitization for non-issue pages

### Phase 27: Project Hub & Issue Views
**Goal**: Projects serve as hubs with embedded issue database views and visual page identity via emoji icons
**Depends on**: Phase 26
**Requirements**: HUB-01, HUB-02, HUB-03, HUB-04
**Success Criteria** (what must be TRUE):
  1. User can view project issues as Board, List, or Table embedded directly within the project page
  2. User can switch between issue views (Board/List/Table) via a toolbar and the selected view persists per project
  3. User can view issues grouped by priority swimlanes in a dedicated Priority view
  4. User can set an emoji icon on any page and sees it displayed in the sidebar tree and page header
**Plans**: 2 plans

Plans:
- [ ] 27-01-PLAN.md — Project hub page, per-project view persistence, Priority view
- [ ] 27-02-PLAN.md — Emoji icon migration, backend schema, frontend render and picker

### Phase 28: Visual Design Refresh
**Goal**: The application looks and feels Notion-like with refined typography, spacing, and colors
**Depends on**: Phase 27
**Requirements**: UI-01
**Success Criteria** (what must be TRUE):
  1. Typography uses system font stack with consistent heading hierarchy and body text sizing
  2. Spacing follows an 8px grid system with consistent padding and margins across all pages
  3. Color palette is muted and professional with proper dark mode parity
  4. Existing pages (issues, settings, AI chat) retain correct layout and readability after token changes
**Plans**: 2 plans

Plans:
- [ ] 28-01-PLAN.md — Design token update: system font stack, neutral Notion-like color palette, dark mode parity, neutral shadows
- [ ] 28-02-PLAN.md — Page-level 8px grid spacing audit and visual verification checkpoint

### Phase 29: Responsive Layout & Drag-and-Drop
**Goal**: The application adapts gracefully to tablet viewports and users can reorganize the page tree via drag-and-drop
**Depends on**: Phase 28
**Requirements**: UI-02, UI-03, UI-04
**Success Criteria** (what must be TRUE):
  1. Sidebar collapses to an icon rail or overlay on tablet viewports (768-1024px) without breaking navigation
  2. Content area adjusts layout (reduced margins, stacked elements) for tablet viewport
  3. User can drag a page in the sidebar tree to reorder among siblings
  4. User can drag a page in the sidebar tree to re-parent it under a different node, with depth limit enforced visually
**Plans**: 3 plans

Plans:
- [ ] 29-01-PLAN.md — Tablet icon-rail sidebar behavior, mobile/tablet/desktop viewport differentiation
- [ ] 29-02-PLAN.md — Drag-and-drop tree reordering: API methods, mutation hooks, DndContext in ProjectPageTree
- [ ] 29-03-PLAN.md — Gap closure: depth limit visual enforcement during drag-and-drop

## Progress

**Execution Order:**
Phases execute in numeric order: 24 → 25 → 26 → 27 → 28 → 29

| Phase | Milestone | Plans | Status | Completed |
|-------|-----------|-------|--------|-----------|
| 1–11 | v1.0 | 46/46 | Complete | 2026-03-09 |
| 12–23 | v1.0-alpha | 37/37 | Complete | 2026-03-12 |
| 24. Page Tree Data Model | 2/2 | Complete    | 2026-03-12 | - |
| 25. Tree API & Page Service | 2/2 | Complete    | 2026-03-12 | - |
| 26. Sidebar Tree & Navigation | 3/3 | Complete    | 2026-03-12 | - |
| 27. Project Hub & Issue Views | 2/2 | Complete    | 2026-03-12 | - |
| 28. Visual Design Refresh | 2/2 | Complete    | 2026-03-12 | - |
| 29. Responsive & Drag-and-Drop | 3/3 | Complete    | 2026-03-12 | - |

**Total: 29 phases, 92 plans, 86 requirements**

---
*v1.0 shipped: 2026-03-09 — 11 phases, 46 plans, 30/30 requirements*
*v1.0-alpha shipped: 2026-03-12 — 12 phases, 37 plans, 39/39 requirements + 7 gap closure items*
*v1.0.0-alpha2 started: 2026-03-12 — 6 phases, 17 requirements*

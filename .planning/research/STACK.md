# Stack Research

**Domain:** Notion-style page tree, responsive layout, visual design refresh for existing SDLC platform
**Researched:** 2026-03-12
**Confidence:** HIGH

## Scope

Stack additions/changes needed for:
1. Nested page tree (parent/child, max 3 levels) in sidebar and project views
2. Responsive sidebar/layout (desktop 1280px+ and tablet 768-1024px)
3. Notion-like visual design polish (typography, spacing, colors)

**Existing stack (DO NOT change):** Next.js 16.1, React 19.2, MobX 6, TanStack Query 5, shadcn/ui, TipTap 3, Tailwind CSS 4, @dnd-kit (core + sortable), react-resizable-panels, Motion (framer-motion), PostgreSQL 16, SQLAlchemy async, FastAPI.

## Key Finding: Almost Everything Needed Already Exists

The codebase already has the foundational libraries for all three features. The primary gaps are:

1. **Backend:** No `parent_id` / tree structure on the Note model -- needs a migration, not a new library
2. **Frontend tree UI:** Existing `@dnd-kit/core` + `@dnd-kit/sortable` are sufficient for a 3-level tree. A dedicated tree library adds unnecessary complexity for this shallow depth.
3. **Responsive:** `useResponsive()` hook, `AppShell` with mobile overlay sidebar, and `react-resizable-panels` already exist
4. **Design polish:** Tailwind CSS 4 design tokens, custom CSS variables, DM Sans + Fraunces fonts already configured

## Recommended Stack Additions

### New Libraries: NONE Required

No new npm packages or Python packages are needed. The existing stack handles all three features.

**Rationale:** Adding a tree library (react-arborist, headless-tree, etc.) is unnecessary when the page tree is limited to 3 levels with at most ~100 nodes per project. The existing `@dnd-kit/core` + `@dnd-kit/sortable` already powers the `OutlineTree.tsx` component with drag-and-drop reordering. Extending it to support nested levels is straightforward with indentation-based rendering and parent_id tracking.

### Backend: Schema Changes Only

| Change | What | Why |
|--------|------|-----|
| `parent_id` column on `notes` | Self-referential FK: `ForeignKey("notes.id", ondelete="CASCADE")` | Adjacency list for parent/child hierarchy |
| `position` column on `notes` | `Integer, nullable=False, default=0` | Sibling ordering within parent |
| `page_type` column on `notes` | `String(20)` enum: `"project"`, `"personal"` | Distinguish project pages vs user personal pages |
| Composite index | `(workspace_id, parent_id, position)` | Efficient tree queries per workspace |
| Check constraint | `depth <= 3` enforced via app layer or DB trigger | Prevent exceeding 3-level nesting |

**Why adjacency list over materialized path (ltree):**
- Max depth is 3 -- recursive CTE overhead is negligible
- Re-parenting (drag-drop move) is a single UPDATE on `parent_id` (adjacency list) vs rewriting all descendant paths (materialized path)
- Adjacency list matches SQLAlchemy's native self-referential relationship pattern
- ltree adds a PostgreSQL extension dependency for zero benefit at this depth
- The existing codebase has no ltree usage; adjacency list is consistent

**SQLAlchemy self-referential pattern (already supported, no new library):**
```python
# On Note model
parent_id: Mapped[uuid.UUID | None] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("notes.id", ondelete="CASCADE"),
    nullable=True,
)
position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

children: Mapped[list["Note"]] = relationship(
    "Note",
    back_populates="parent",
    cascade="all, delete-orphan",
    lazy="selectin",
    order_by="Note.position",
)
parent: Mapped["Note | None"] = relationship(
    "Note",
    back_populates="children",
    remote_side="Note.id",
    lazy="joined",
)
```

### Frontend: Extend Existing Components

| Area | Existing Asset | Extension Needed |
|------|---------------|-----------------|
| Tree sidebar | `OutlineTree.tsx` (uses @dnd-kit) | Add nesting support: indentation levels, expand/collapse state, parent_id awareness |
| Drag-drop | `@dnd-kit/core` ^6.3.1 + `@dnd-kit/sortable` ^10.0.0 | Use `SortableContext` with indentation offset to handle nested drops (already installed) |
| Responsive layout | `AppShell.tsx` + `useResponsive()` hook | Add tablet-specific sidebar width (200px collapsed, 260px expanded) |
| Resizable panels | `react-resizable-panels` ^4.4.2 | Use for project page split: tree panel + content panel |
| Animations | `motion` ^12.28.1 | Already used for sidebar transitions; extend for tree expand/collapse |
| Collapsible | `@radix-ui/react-collapsible` ^1.1.12 | Already installed; use for tree node expand/collapse |
| Design tokens | `globals.css` with CSS custom properties | Refine spacing scale, add Notion-inspired subtle borders and hover states |

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Adjacency list (parent_id) | PostgreSQL ltree extension | Overkill for max 3 levels; adds extension dependency; re-parenting is costlier |
| Adjacency list (parent_id) | Nested sets / modified preorder | Write-heavy operations (insert/move) are expensive; depth is too shallow to benefit from fast subtree reads |
| Adjacency list (parent_id) | Closure table | Requires extra junction table; unnecessary for 3 levels |
| @dnd-kit (existing) | react-arborist (3.4.3) | Adds ~15kB; depends on react-window (already have react-virtuoso); API designed for deep trees we don't need |
| @dnd-kit (existing) | @headless-tree/react (1.6.3) | Clean API but adds a new dependency for a problem solvable with existing @dnd-kit + 100 lines of nesting logic |
| @dnd-kit (existing) | dnd-kit-sortable-tree | Thin wrapper around @dnd-kit we already have; unnecessary abstraction layer |
| Tailwind CSS 4 tokens | CSS-in-JS (Emotion, styled-components) | Contradicts existing architecture; Tailwind v4 CSS-first approach is already in place |
| Tailwind spacing refinement | Tailwind UI / shadcn themes | Already using shadcn/ui; design polish is token-level CSS changes, not a library |

## What NOT to Add

| Avoid | Why | What to Do Instead |
|-------|-----|-------------------|
| react-arborist | Adds dependency + bundle size for a 3-level tree; @dnd-kit already handles drag-drop | Build 100-line TreeNode component using @dnd-kit + recursive rendering |
| @headless-tree/react | Same reasoning; headless API is elegant but unnecessary overhead | Existing @dnd-kit + Radix Collapsible covers the UX |
| CSS framework changes | Tailwind v4 with design tokens is already configured | Refine existing CSS variables in `globals.css` |
| New font packages | DM Sans (body), Fraunces (display), DM Mono (code), JetBrains Mono (gutter) already loaded | Adjust font weights and sizes in Tailwind theme for Notion-like feel |
| react-beautiful-dnd | Deprecated; @dnd-kit is its spiritual successor and already installed | N/A |
| Y.js collaborative editing | Explicitly out of scope per PROJECT.md | Already in package.json as dependency but not needed for this milestone |
| Zustand for tree state | MobX is the state management choice (DD from pattern 45) | Use MobX store for tree expand/collapse and drag state |
| shadcn/ui sidebar component | Project uses custom sidebar built on Radix primitives | Extend existing `Sidebar.tsx`; shadcn sidebar would conflict |
| Any new backend Python packages | SQLAlchemy adjacency list is built-in; recursive CTE queries need no extensions | N/A |

## Stack Patterns for This Milestone

**For nested page tree:**
- Backend: adjacency list with `parent_id` + `position` on existing `notes` table
- Frontend: recursive `TreeNode` component rendering with @dnd-kit `SortableContext` per level
- State: MobX store for tree expand/collapse state (persisted in localStorage per user)
- API: Single endpoint returns flat list with `parent_id`; client builds tree structure

**For responsive layout:**
- Use existing `useResponsive()` hook breakpoints: mobile (<768), tablet (768-1024), desktop (1024+)
- Sidebar: collapsed by default on tablet, auto-collapse on navigate (already implemented)
- Content area: `react-resizable-panels` for project page split view (tree | content)
- No new responsive libraries needed

**For visual design refresh:**
- Refine CSS custom properties in `globals.css` `:root` block
- Adjust spacing: tighter padding in sidebar items (Notion uses 4-6px vertical, currently 6px)
- Softer hover states: reduce opacity of `sidebar-accent` hover
- Typography: slightly reduce base font size in sidebar (currently xs/12px, Notion uses 14px body but 13px sidebar)
- Border refinement: use `border-subtle` more consistently; Notion uses very light 1px borders
- These are all CSS token changes, not library additions

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| @dnd-kit/core ^6.3.1 | @dnd-kit/sortable ^10.0.0 | Already installed and working together in OutlineTree.tsx |
| @dnd-kit/sortable ^10.0.0 | React 19.2 | Confirmed working in current codebase |
| react-resizable-panels ^4.4.2 | React 19.2 | Already in use |
| @radix-ui/react-collapsible ^1.1.12 | React 19.2 | Already in use |
| motion ^12.28.1 | React 19.2 | Already powering sidebar animations |
| SQLAlchemy ^2.0.36 | Self-referential relationships | Built-in; adjacency list pattern is core SQLAlchemy |

## Installation

```bash
# No new packages required.
# All dependencies already exist in package.json and pyproject.toml.

# Backend: only need a new Alembic migration
cd backend && alembic revision --autogenerate -m "add_page_tree_hierarchy"

# Frontend: no installs needed
```

## Sources

- [react-arborist npm](https://www.npmjs.com/package/react-arborist) -- v3.4.3, last published ~1 year ago, confirmed React 19 support
- [@headless-tree/react npm](https://www.npmjs.com/package/@headless-tree/react) -- v1.6.3, actively maintained successor to react-complex-tree
- [@dnd-kit docs](https://docs.dndkit.com/presets/sortable) -- sortable preset with nested context support
- [dnd-kit-sortable-tree](https://github.com/Shaddix/dnd-kit-sortable-tree) -- community tree implementation on @dnd-kit
- [PostgreSQL hierarchical data patterns](https://www.ackee.agency/blog/hierarchical-models-in-postgresql) -- adjacency list vs ltree vs nested sets comparison
- [Materialized path in PostgreSQL](https://sqlfordevs.com/tree-as-materialized-path) -- path-based alternative analysis
- Existing codebase analysis: `OutlineTree.tsx`, `app-shell.tsx`, `sidebar.tsx`, `useMediaQuery.ts`, `globals.css`, Note model, Project model

---
*Stack research for: Notion-style page tree + responsive layout + visual design refresh*
*Researched: 2026-03-12*

# Pitfalls Research

**Domain:** Adding nested page tree, project-centric navigation, responsive layout, and visual design refresh to existing SDLC platform (Pilot Space v1.0.0-alpha2)
**Researched:** 2026-03-12
**Confidence:** HIGH (based on direct codebase analysis of existing models, stores, sidebar, and app shell)

## Critical Pitfalls

### Pitfall 1: Flat-to-Tree Migration Breaks Existing Note References

**What goes wrong:**
The current `notes` table has a flat structure with `workspace_id` and optional `project_id`. Adding `parent_id` for tree hierarchy requires a data migration that re-parents all existing notes. Existing foreign keys (note_issue_links, note_note_links, note_annotations, ai_sessions.source_chat_session_id, knowledge graph NOTE/NOTE_CHUNK nodes) all reference note IDs. If the migration changes note ownership semantics (workspace-level notes become "personal pages" or get moved under projects), any query that assumed `project_id IS NULL` means "workspace-level" will silently return wrong results.

**Why it happens:**
The requirement says "remove workspace-level notes" and replace with project-level pages + user-level personal pages. This is a semantic change to existing data, not just adding a column. Developers focus on the new schema and forget that existing queries, RLS policies, and the knowledge graph all depend on the current ownership model.

**How to avoid:**
1. Add `parent_id` and `page_type` (project_page / personal_page) columns in a migration without removing any existing columns yet.
2. Write a data migration that classifies existing notes: notes with `project_id` become project pages, notes without become personal pages owned by `owner_id`.
3. Keep `workspace_id` on all notes (RLS depends on it). Never remove the workspace scope -- it is the multi-tenant boundary.
4. Update RLS policies in the same migration to account for personal pages (user can only see their own personal pages, but all workspace members see project pages).
5. Run the migration against a clone of production data before deploying.

**Warning signs:**
- Notes disappearing after migration (RLS filtering them out due to changed semantics)
- Knowledge graph `NOTE_CHUNK` nodes with dangling references
- `NoteStore.loadNotes()` returning empty lists because the API endpoint filters changed
- Sidebar pinned/recent sections showing stale or missing notes

**Phase to address:**
Phase 1 (Data Model & Migration) -- must be the first phase before any UI work begins.

---

### Pitfall 2: Recursive Tree Queries Causing N+1 or Infinite Loops

**What goes wrong:**
A 3-level page tree requires fetching parent-child relationships recursively. Naive implementations either: (a) issue one query per node (N+1), (b) load the entire workspace's page tree on every sidebar render, or (c) introduce infinite loops if a circular parent reference sneaks in (parent_id points to a descendant). PostgreSQL recursive CTEs solve this but need careful depth limiting.

**Why it happens:**
SQLAlchemy's `relationship()` with `remote_side` for self-referential trees defaults to lazy loading, which causes N+1 in async contexts. The existing codebase already has N+1 guardrails (selectinload/joinedload patterns), but a self-referential tree is a new pattern not yet used in this codebase. The 3-level depth limit is a business rule that must be enforced at both DB and application layers.

**How to avoid:**
1. Use a PostgreSQL recursive CTE wrapped in a repository method, not SQLAlchemy relationship traversal: `WITH RECURSIVE page_tree AS (SELECT ... WHERE parent_id IS NULL UNION ALL SELECT ... FROM pages JOIN page_tree ...)`.
2. Add a `depth` column (0, 1, 2) computed on insert/move. Enforce `CHECK (depth <= 2)` at the DB level.
3. Add a unique constraint or trigger preventing circular references: `CHECK (id != parent_id)` plus application-level validation that walks up at most 3 levels.
4. Load the full tree for a project in one query (projects have bounded page counts). Cache in MobX store.
5. Add a `position` integer column for sibling ordering within a parent.

**Warning signs:**
- Sidebar tree taking >500ms to render (N+1 queries)
- Backend logs showing dozens of SELECT statements per page tree load
- "Maximum recursion depth" errors in recursive CTE (circular reference)
- Pages appearing at wrong depth after drag-and-drop reordering

**Phase to address:**
Phase 1 (Data Model) for schema design, Phase 2 (Backend API) for CTE queries.

---

### Pitfall 3: TipTap Property Block Coupling Blocks Page Reuse

**What goes wrong:**
The existing TipTap editor is tightly coupled with issue-specific property blocks (PropertyBlockNode, PropertyBlockView, guard plugins preventing deletion/movement). When the same editor needs to render project pages and personal pages (which have no issue properties), the property block extension either crashes, renders empty, or the guard plugins prevent normal editing behavior on non-issue pages.

**Why it happens:**
The property block is hardcoded as position-0 in the TipTap document with ProseMirror guard plugins that prevent deletion/movement. The `IssueNoteContext` bridge pattern feeds issue data into the editor. For non-issue pages, there is no IssueNoteContext, and the PropertyBlockNode will read undefined context values. The `.claude/rules/tiptap.md` explicitly warns that `IssueEditorContent` must NOT be wrapped in `observer()` due to the React 19 flushSync issue.

**How to avoid:**
1. Extract a base `PageEditor` component that has NO property block extension. The issue editor becomes `PageEditor + PropertyBlockExtension`.
2. Project pages and personal pages use `PageEditor` directly (no property block, no guard plugins).
3. Do NOT try to make the property block "optional" within the same editor instance -- the guard plugins use ProseMirror plugin state that assumes the block exists.
4. Share TipTap extensions (slash commands, ghost text, formatting) via a shared extension kit. Issue-specific extensions are layered on top.
5. Keep the `IssueNoteContext` bridge pattern for issue pages only. Page pages get a simpler `PageContext` (title, parent, breadcrumb).

**Warning signs:**
- "Cannot read properties of undefined" errors when opening a non-issue page in the editor
- ProseMirror guard plugin throwing when property block node is not at position 0
- Ghost text and slash commands not working on project pages (extension registration order issue)
- The React 19 nested `flushSync` error reappearing (MobX observer wrapping the wrong component)

**Phase to address:**
Phase 3 (Editor Refactoring) -- after data model and API are stable, before building the page tree UI.

---

### Pitfall 4: Sidebar State Explosion From Tree + Expand/Collapse

**What goes wrong:**
The current sidebar is a flat list of nav items + pinned/recent notes. Converting it to a tree with expandable projects, each containing a 3-level page tree, pinned shortcuts, and recent items creates a state explosion: which projects are expanded, which tree nodes are expanded, scroll position, active node highlight, drag targets. Putting all this in MobX `UIStore` makes it a god object. Putting it in component state loses persistence across navigation.

**Why it happens:**
The existing `UIStore` only tracks `sidebarCollapsed` and `sidebarWidth`. The existing `NoteStore` loads a flat list. Neither is designed for hierarchical expand/collapse state. Developers tend to add tree state as an afterthought, leading to janky UX where the tree collapses on every navigation or re-renders the entire tree on any state change.

**How to avoid:**
1. Create a dedicated `PageTreeStore` (MobX) that manages: expanded node IDs (Set), loaded subtrees (Map), and active page ID.
2. Persist expanded state per-user in `localStorage` keyed by workspace slug + project ID.
3. Use `observable.shallow` for the tree data to prevent deep MobX tracking on every nested page object.
4. Virtualize the sidebar tree if any project has >50 pages (unlikely at 3-level max, but defensive).
5. Load tree data lazily per-project: only fetch children when a project node is expanded for the first time.

**Warning signs:**
- Sidebar re-rendering on every keystroke in the editor (MobX over-observation)
- Tree collapsing to root on every page navigation
- Sidebar scroll position resetting when switching pages
- "New page" action not appearing in tree until manual refresh

**Phase to address:**
Phase 4 (Sidebar & Navigation UI) -- after the API can serve tree data.

---

### Pitfall 5: Visual Design Refresh Breaks Existing Component Contracts

**What goes wrong:**
A "Notion-like" visual refresh means changing typography, spacing, colors, and component styling. With shadcn/ui, these changes propagate through CSS variables and Tailwind classes. Changing `--radius`, `--primary`, or font sizes globally affects every existing page (settings, members, cycles, AI chat, approvals). Components that used hardcoded `px-4 py-2` values or specific color classes will look inconsistent with the new design tokens.

**Why it happens:**
shadcn/ui components are copy-pasted into the project (not a dependency). Each component may have been customized with hardcoded values. A global CSS variable change affects some components but not others, creating visual inconsistency. The existing 880K-line codebase has hundreds of component files with Tailwind classes that may conflict with new design tokens.

**How to avoid:**
1. Create a design token changeset document BEFORE touching CSS: list every variable being changed and its old/new values.
2. Change design tokens in `globals.css` first, then audit every page visually (screenshot comparison).
3. Do NOT change component-level Tailwind classes during the token phase. Token changes and component refactoring are separate passes.
4. Add a Storybook or visual regression test for critical components (sidebar, editor, issue detail) before the refresh.
5. Use CSS custom properties for NEW design values (e.g., `--page-tree-indent`, `--sidebar-tree-font`) rather than overriding existing tokens that affect the whole app.

**Warning signs:**
- Settings page suddenly having wrong padding/colors after a "sidebar-only" CSS change
- Buttons or badges becoming unreadable due to contrast changes
- Dark mode breaking because only light mode tokens were updated
- The TipTap editor toolbar losing its styling (it uses custom CSS that may not inherit design tokens)

**Phase to address:**
Phase 5 (Visual Design Refresh) -- should be its own dedicated phase AFTER all structural UI changes are complete.

---

### Pitfall 6: Responsive Layout Retrofit Collides With Existing Mobile Handling

**What goes wrong:**
The codebase already has responsive handling: `useResponsive()` hook, `isSmallScreen` checks in `AppShell`, mobile sidebar overlay, `NoteCanvasMobileLayout`. Adding tablet-specific breakpoints (768-1024px) may conflict with existing `isSmallScreen` which groups mobile AND tablet together (`isMobile || isTablet`). Components that check `isSmallScreen` will behave as "mobile" on tablets, but the new requirement wants tablet to have its own layout (collapsible sidebar, adapted content width).

**Why it happens:**
The existing `useResponsive()` hook already defines `isTablet` as a separate breakpoint (768-1024px), but `isSmallScreen` lumps tablet with mobile. Code throughout the app uses `isSmallScreen` as the sole responsive check. Changing `isSmallScreen` to exclude tablets would break every existing responsive behavior. Not changing it means tablets get the mobile experience.

**How to avoid:**
1. Do NOT change the semantics of existing `isSmallScreen`. It is used in sidebar.tsx, app-shell.tsx, and at least 7 other files.
2. Add a new hook or extend `useResponsive()` with `isTabletLayout` that specifically targets 768-1024px for the new tablet behavior.
3. Refactor responsive checks incrementally: start with AppShell and Sidebar (the layout boundary), then propagate to content pages.
4. Tablet layout should be "desktop with collapsed sidebar by default" -- not a separate layout component. This minimizes the delta from existing desktop layout.
5. Test on actual tablet viewport (1024x768) and iPad Pro (1366x1024) during development, not just Chrome responsive mode.

**Warning signs:**
- Tablet showing mobile overlay sidebar when it should show inline collapsed sidebar
- Content area being too narrow on tablet because it still applies mobile padding
- Editor toolbar wrapping or overflowing on tablet width
- Existing `NoteCanvasMobileLayout` activating on tablet when it should not

**Phase to address:**
Phase 6 (Responsive Layout) -- after all desktop UI is stable, as a separate responsive pass.

---

### Pitfall 7: Embedded Issue Database Views Creating Circular Dependencies

**What goes wrong:**
The requirement calls for embedded issue database views (Board, List, Timeline, Priority) inside project pages. This means the page editor component needs to render issue views, and issue views may link back to pages. If the `PageTreeStore` imports from `IssueStore` and `IssueStore` needs page context for navigation, you get a circular dependency between MobX stores. Similarly, the Next.js route structure (`/[workspaceSlug]/projects/[projectId]/pages/[pageId]`) needs to coexist with (`/[workspaceSlug]/issues/[issueId]`).

**Why it happens:**
The existing architecture has clean store boundaries: `NoteStore` and `IssueStore` are independent. Embedding issue views inside project pages crosses this boundary. The `IssueViewStore` already exists separately, but it was designed for a standalone issues page, not for embedded rendering within a page editor.

**How to avoid:**
1. Embedded issue views should be read-only query components that accept `projectId` as a prop and fetch independently via TanStack Query -- NOT through `IssueStore` MobX state.
2. Keep `IssueStore` and `PageTreeStore` independent. Communication happens through URL navigation and TanStack Query cache, not store-to-store references.
3. Embedded views are NOT TipTap nodes. They are React components rendered alongside the editor in the page layout (like Notion's "linked database" -- it is a page section, not an editor block).
4. Route structure: `/projects/[projectId]` shows project hub with page tree + embedded views. Individual pages are `/projects/[projectId]/pages/[pageId]`. Issues remain at `/issues/[issueId]`.

**Warning signs:**
- Circular import errors at build time
- Issue view inside a project page showing stale data (MobX store was loaded for a different context)
- Navigation from embedded issue view losing the project context (back button goes to wrong place)
- TanStack Query cache key collisions between standalone and embedded issue views

**Phase to address:**
Phase 4 (Project Hub UI) -- design the component boundary before building either the page tree or embedded views.

---

### Pitfall 8: RLS Policy Gaps on New Page Ownership Model

**What goes wrong:**
The two-ownership model (project pages visible to workspace, personal pages visible only to owner) requires new RLS policies. The existing notes RLS policy grants access based on `workspace_id` + membership. Personal pages need an additional clause: `owner_id = current_setting('app.current_user_id')::uuid`. If this is not added atomically with the schema migration, personal pages either leak to all workspace members or become invisible to their owner.

**Why it happens:**
The existing RLS policies on `notes` use workspace membership as the access boundary. The new model adds a second access path (owner-only for personal pages). Developers may add the `page_type` column but forget to update the RLS SELECT policy, leaving personal pages exposed. Or they may add the owner check but forget to OR it with the project-page workspace check, making project pages invisible.

**How to avoid:**
1. The RLS SELECT policy must be: `(page_type = 'project_page' AND workspace_member_check) OR (page_type = 'personal_page' AND owner_id = current_user_id)`.
2. Write the RLS policy in the SAME migration that adds `page_type`. Never have a window where the column exists without the policy.
3. Add integration tests with `TEST_DATABASE_URL` (real PostgreSQL, not SQLite) that verify: (a) user A cannot see user B's personal pages, (b) both users can see project pages, (c) service_role bypasses both.
4. Remember the known bug: RLS enum values must be UPPERCASE in policies even if stored lowercase.

**Warning signs:**
- Personal pages visible in another user's "Notes" section
- A user's personal pages disappearing after the migration (policy too restrictive)
- Tests passing on SQLite but failing on PostgreSQL (SQLite skips RLS entirely)

**Phase to address:**
Phase 1 (Data Model & Migration) -- RLS must be part of the schema migration, not an afterthought.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip depth column, compute on read | Faster initial migration | Every tree query needs recursive computation; no DB-level constraint on max depth | Never -- depth column is cheap and critical for the 3-level constraint |
| Reuse NoteStore for page tree | No new store creation | NoteStore becomes a god store mixing flat lists and tree state; all note consumers re-render on tree changes | Never -- create PageTreeStore from the start |
| Inline responsive checks per-component | Quick fix for each component | Inconsistent breakpoint behavior across pages; some components responsive, others not | Only during Phase 6 transition -- extract to shared layout components after |
| Hardcode Notion colors instead of using design tokens | Faster visual matching | Theme switching breaks; dark mode requires separate fixes; future design changes touch every file | Never -- always use CSS custom properties |
| Store tree expand state in component state | Simple React implementation | State lost on navigation; sidebar tree collapses every time user clicks a link | Never -- must persist in localStorage or MobX |
| Use SQLAlchemy self-referential relationship for tree | Less custom SQL | N+1 on every tree load; async context makes lazy loading fail silently | Only for single-node parent lookups, never for full tree loads |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Knowledge Graph (kg_populate_handler) | Adding page tree without updating the kg_populate handler -- NOTE_CHUNK nodes reference note IDs that may change semantics | Update `kg_populate_handler.py` to handle page_type: only populate from content pages, skip empty container pages |
| Meilisearch Index | Notes index assumes flat structure; adding parent/child pages without updating search index means search results lack tree context (breadcrumb) | Add `parent_title` and `breadcrumb` fields to the Meilisearch note document; update the indexing pipeline |
| TipTap Auto-Save | Current auto-save strips `data-property-block` div; new page types may have different strip logic (or none) | Parameterize the content-strip function per page type rather than hardcoding property block stripping |
| Cmd+K Command Palette | Currently searches notes and issues as flat lists; must now show page hierarchy in results | Add breadcrumb display to search results; search API returns parent chain |
| Supabase Realtime (future) | If real-time collaborative editing is added later, tree moves (re-parenting) need conflict resolution | Design parent_id updates as explicit "move" operations with optimistic locking (version column) even if not using realtime yet |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading full page tree for all projects on sidebar mount | Sidebar takes 2-3s to render; API returns hundreds of pages across all projects | Lazy-load: fetch tree only for expanded projects; cache in PageTreeStore per project ID | >10 projects with >20 pages each |
| Re-rendering entire sidebar tree on any MobX state change | Sidebar jank when typing in editor (noteStore changes trigger sidebar re-render) | Use `observer()` on leaf tree nodes, not the entire sidebar; use `observable.shallow` for tree data | Any page with active auto-save |
| Recursive CTE without depth limit | Query takes exponential time if circular reference exists or depth is unbounded | `WHERE depth < 3` in CTE; `CHECK (depth <= 2)` constraint on table | First circular reference in data |
| CSS layout recalculation on sidebar expand/collapse | Content area janks during sidebar animation; editor loses cursor position | Use CSS `transform` for sidebar animation (already done); ensure editor container has `will-change: width` | Desktop with sidebar animation |
| Fetching embedded issue views on every project page render | Project hub page takes 3-5s with 4 database views each making separate API calls | Batch API endpoint: `GET /projects/{id}/hub` returns page tree + issue counts + recent activity in one call | Any project with >50 issues |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Personal pages accessible via direct URL without owner check | Any workspace member can read another member's private notes by guessing/enumerating page IDs | RLS policy with owner_id check for personal pages; API endpoint must also validate, not just rely on RLS (defense in depth) |
| Tree move operation not checking destination permissions | User could move a personal page into a project (exposing it) or a project page into personal space (hiding it from team) | Move endpoint must validate: personal pages can only move within personal tree; project pages can only move within same project |
| Parent_id manipulation to access cross-workspace pages | Setting parent_id to a page in another workspace bypasses workspace isolation | Foreign key constraint: parent page must have same workspace_id; RLS on INSERT/UPDATE validates workspace match |
| Breadcrumb leak in search results | Search result shows parent page titles that the user should not have access to (e.g., another user's personal page is a parent -- should be impossible but worth checking) | Breadcrumb assembly must go through the same RLS-filtered query, not a service_role query |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Tree drag-and-drop without undo | User accidentally moves a page to wrong location; no way to recover position | Implement undo for tree moves (toast with "Undo" button, 5s timeout); store previous parent_id + position |
| No empty state for project page tree | New project shows blank sidebar section; user does not know they can create pages | Show "Create your first page" placeholder with one-click page creation inside the project tree |
| Breadcrumb overflow on deep pages | 3-level breadcrumb like "Project > Parent Page > Child Page > Current Page" overflows on tablet | Truncate middle breadcrumb segments with ellipsis; show full path on hover |
| Collapsing sidebar hides page tree context | User working in a nested page collapses sidebar; loses context of where they are in the tree | Show breadcrumb in the content header area (above editor) regardless of sidebar state |
| Design refresh changes colors without updating the editor | Note canvas and issue editor have custom styling that does not inherit from the design system refresh | Audit all TipTap CSS (prose classes, node view styles, toolbar) as part of the design refresh |
| Forced migration of existing notes confuses users | Users log in and their familiar flat notes list is gone, replaced by a tree they did not ask for | Show a one-time migration notice; auto-organize existing notes into a "Migrated Notes" section at root level; let users reorganize at their pace |

## "Looks Done But Isn't" Checklist

- [ ] **Page tree:** Often missing sibling reordering -- verify drag-and-drop within same parent works, not just cross-parent moves
- [ ] **Page tree:** Often missing keyboard navigation -- verify Arrow Up/Down/Left/Right traverses and expands/collapses tree nodes
- [ ] **Responsive layout:** Often missing edge cases at exactly 1024px -- verify the tablet/desktop breakpoint transition is smooth (no layout jump)
- [ ] **Design refresh:** Often missing dark mode -- verify every new/changed component in both light and dark themes
- [ ] **Design refresh:** Often missing the TipTap editor styling -- verify headings, code blocks, blockquotes, and slash command menu match new design tokens
- [ ] **Embedded issue views:** Often missing empty states -- verify Board/List/Timeline/Priority views show meaningful empty state when project has no issues
- [ ] **Personal pages:** Often missing the "no project" case -- verify personal pages are accessible when user is not a member of any project
- [ ] **Tree operations:** Often missing optimistic updates -- verify creating/moving/deleting a page updates the sidebar tree immediately without waiting for API response
- [ ] **RLS:** Often missing test coverage on SQLite -- verify all tree permission tests run against real PostgreSQL with `TEST_DATABASE_URL`
- [ ] **Migration:** Often missing rollback path -- verify `alembic downgrade` works for the tree migration and does not lose data

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Flat-to-tree migration corrupts note ownership | HIGH | Restore from backup; rewrite migration with proper data classification; re-run on staging first |
| N+1 queries on tree load | LOW | Replace SQLAlchemy relationship traversal with recursive CTE in repository layer; no schema change needed |
| TipTap property block crashes on non-issue pages | MEDIUM | Extract base PageEditor; requires refactoring editor component hierarchy and updating all page routes |
| Sidebar state explosion / god store | MEDIUM | Extract PageTreeStore from UIStore/NoteStore; refactor all sidebar tree consumers to use new store |
| Design token change breaks existing pages | LOW | Revert CSS variable changes; apply tokens incrementally per-component instead of globally |
| RLS policy gap exposes personal pages | HIGH | Emergency hotfix: add owner_id check to RLS SELECT policy; audit access logs for any unauthorized reads |
| Responsive breakpoint conflict | LOW | Add new `isTabletLayout` check without changing `isSmallScreen`; update components incrementally |
| Circular dependency between stores | MEDIUM | Refactor to use TanStack Query for cross-feature data; remove store-to-store imports |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Flat-to-tree migration breaks references | Phase 1: Data Model & Migration | Run migration on staging data dump; verify note counts before/after; check KG node references |
| Recursive tree N+1 queries | Phase 2: Backend API | Load test with 50-page project; verify single CTE query in SQL logs |
| TipTap property block coupling | Phase 3: Editor Refactoring | Open a non-issue page; verify no console errors; verify slash commands work |
| Sidebar state explosion | Phase 4: Sidebar & Navigation UI | Navigate between 5 pages rapidly; verify tree expand state persists; profile MobX re-renders |
| Design refresh breaks existing pages | Phase 5: Visual Design Refresh | Screenshot comparison of all existing pages before/after token changes |
| Responsive layout conflicts | Phase 6: Responsive Layout | Test at 768px, 1024px, 1280px breakpoints; verify no layout jumps |
| Embedded issue view circular deps | Phase 4: Project Hub UI | Build succeeds with no circular import warnings; embedded views fetch independently |
| RLS policy gaps | Phase 1: Data Model & Migration | Integration tests with real PostgreSQL; cross-user page visibility tests |

## Sources

- Direct codebase analysis: `backend/src/pilot_space/infrastructure/database/models/note.py` (current flat schema)
- Direct codebase analysis: `frontend/src/components/layout/sidebar.tsx` (current flat nav, 671 lines)
- Direct codebase analysis: `frontend/src/components/layout/app-shell.tsx` (current responsive handling)
- Direct codebase analysis: `frontend/src/hooks/useMediaQuery.ts` (existing breakpoint definitions)
- Direct codebase analysis: `frontend/src/stores/RootStore.ts` (12 independent stores, no tree state)
- Project rules: `.claude/rules/tiptap.md` (PropertyBlockNode constraints, flushSync issue)
- Project rules: `.claude/rules/rls-check.md` (RLS policy requirements)
- Project rules: `.claude/rules/migration.md` (immutable migrations, chain validation)
- Project memory: `MEMORY.md` (known RLS uppercase/lowercase bug, issue-note architecture)
- PROJECT.md: v1.0.0-alpha2 requirements and constraints

---
*Pitfalls research for: Pilot Space v1.0.0-alpha2 Notion-Style Restructure*
*Researched: 2026-03-12*

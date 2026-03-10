# Implementation Plan: Project Notes Panel

**Branch**: `022-project-notes-panel` | **Date**: 2026-03-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/022-project-notes-panel/spec.md`

## Summary

Add a "Notes" panel to the project sidebar (`ProjectSidebar`) that displays up to 5 pinned and 5 recent notes scoped to the current project. The panel matches the workspace sidebar's PINNED/RECENT visual style. A "New Note" shortcut creates notes pre-linked to the project. This is a **frontend-only** change — no backend modifications are needed.

## Technical Context

**Language/Version**: TypeScript 5.x (strict mode)
**Primary Dependencies**: React 18, TanStack Query v5, MobX 6, Next.js 15 App Router, shadcn/ui, TailwindCSS
**Storage**: N/A (read-only from existing REST API)
**Testing**: Vitest + React Testing Library
**Target Platform**: Web (desktop sidebar, `md:` breakpoint and above)
**Project Type**: Frontend web application (Next.js monorepo)
**Performance Goals**: Panel data loads within the same render cycle as the rest of the project sidebar; no perceived additional delay
**Constraints**: 700-line file limit per constitution; no new backend endpoints; no new backend migrations
**Scale/Scope**: Affects 2 existing files + 1 new component file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|---|---|---|
| Frontend: React 18 + TypeScript strict | ✅ PASS | Existing stack; panel uses same hooks/patterns |
| Frontend: TailwindCSS for styling | ✅ PASS | Panel reuses existing sidebar CSS classes |
| Frontend: Feature-based MobX + TanStack Query | ✅ PASS | Uses `useNotes` (TanStack Query) + `useWorkspaceStore` (MobX) |
| Code: Type check passes | ✅ PASS | No new types; uses existing `Note`, `Project` |
| Code: Lint passes | ✅ PASS | Will verify with `pnpm lint` |
| Code: No TODOs / mocks in production paths | ✅ PASS | Real API calls; real error states |
| Code: File size ≤ 700 lines | ✅ PASS | New component ~150 lines; `ProjectSidebar` delta ~20 lines |
| Security: Auth required for all API calls | ✅ PASS | Existing `notesApi` uses authenticated `apiClient` |
| Architecture: Layer boundaries respected | ✅ PASS | UI layer only; uses existing hooks and API service |
| AI: Human-in-the-loop principle | ✅ N/A | No AI features in this panel |

**Complexity Tracking**: No violations. No new abstractions, no new patterns.

## Project Structure

### Documentation (this feature)

```text
specs/022-project-notes-panel/
├── plan.md              # This file
├── research.md          # Phase 0 output (complete)
├── data-model.md        # Phase 1 output (complete)
├── quickstart.md        # Phase 1 output (complete)
├── contracts/
│   └── api.md           # Phase 1 output (complete)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code

```text
frontend/
└── src/
    └── components/
        └── projects/
            ├── ProjectSidebar.tsx          # MODIFY: mount ProjectNotesPanel below nav
            └── ProjectNotesPanel.tsx       # CREATE: pinned + recent notes panel
```

**Structure Decision**: Frontend-only single-component addition. No backend, no new routes, no new stores. The new component lives alongside `ProjectSidebar` in `components/projects/`.

## Implementation Approach

### 1. Create `ProjectNotesPanel.tsx`

New component at `frontend/src/components/projects/ProjectNotesPanel.tsx`:

```
Props: { project: Project, workspaceSlug: string, workspaceId: string }

Internal structure:
  - Two useNotes calls:
      (a) isPinned: true,  projectId, pageSize: 5 → pinnedNotes
      (b) isPinned: false, projectId, pageSize: 5 → recentNotes
  - useCreateNote for "New Note" mutation
  - useWorkspaceStore for canCreateContent check
  - useRouter for navigation after create

Render:
  - Loading: <Skeleton> rows (3 per section)
  - Error: inline error text
  - Empty (both empty): EmptyNotesState with "New Note" link
  - Has notes:
      Section "Pinned" (if pinnedNotes.length > 0)
        rows + "View all" if total > 5
      Section "Recent" (if recentNotes.length > 0)
        rows + "View all" if total > 5
  - "New Note" button (hidden for guests)
```

**Visual style reference** (`sidebar.tsx` lines 488–544):
- Section header: `text-[10px] font-semibold uppercase tracking-wider text-muted-foreground`
- Row: `flex items-center gap-1.5 rounded-md px-1.5 py-1 text-xs`
- Hover: `hover:bg-sidebar-accent/50`
- Icon: `<FileText className="h-3 w-3 text-muted-foreground" />`

### 2. Modify `ProjectSidebar.tsx`

Add after the `</nav>` closing tag (line 88), inside the `<aside>` desktop block:

```tsx
<Separator className="mx-2 my-2" />
<ProjectNotesPanel
  project={project}
  workspaceSlug={workspaceSlug}
  workspaceId={project.workspaceId}
/>
```

Not added to mobile tab bar (spec FR-009 — desktop sidebar only).

### 3. Write unit tests

File: `frontend/src/components/projects/__tests__/ProjectNotesPanel.test.tsx`

Test cases:
- Renders skeleton when loading
- Renders pinned notes when data available
- Renders recent notes, excludes pinned
- Shows empty state when no notes
- Hides "New Note" for guest role
- Calls create mutation with correct projectId
- Shows "View all" link when total > 5

## Key Reference Patterns

| Pattern | Source |
|---|---|
| Pinned/Recent note lists | `sidebar.tsx` lines 372–544 |
| `useNotes` with projectId filter | `notes/page.tsx` line 330; `useNotes.ts` |
| `useCreateNote` with projectId | `notes/page.tsx` lines 421–434 |
| Guest permission check | `sidebar.tsx` line 267; `notes/page.tsx` line 301 |
| Skeleton loading state | `ProjectSidebar.tsx` lines 22–48 |

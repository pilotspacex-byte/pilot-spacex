# Research: Issue Detail Page

**Feature**: 007-issue-detail-page
**Date**: 2026-02-02

---

## R1: TipTap Reuse for Issue Description Editor

**Decision**: Reuse `createEditorExtensions()` from `frontend/src/features/notes/editor/extensions/createEditorExtensions.ts` with a reduced extension set.

**Rationale**: The note editor already has a production-ready TipTap setup with 13+ extensions. The issue description editor needs a subset: StarterKit, Markdown, Placeholder, CodeBlock, Mention, CharacterCount. Ghost text, margin annotations, slash commands, and issue extraction are not needed for issue descriptions.

**Alternatives considered**:
- Full extension set from notes → Rejected: unnecessary complexity, larger bundle, confusing UX (ghost text in issue description is not spec'd)
- Separate minimal TipTap setup → Rejected: code duplication, divergent formatting behavior
- Plain textarea with markdown preview → Rejected: spec requires rich text editing with live formatting

**Implementation**: Create `createIssueEditorExtensions()` factory that imports individual extensions from the notes editor and assembles a subset. Use `next/dynamic` to code-split the TipTap bundle.

---

## R2: Auto-save Debounce Pattern

**Decision**: Use MobX `reaction()` with 2-second debounce for title/description auto-save. Use immediate TanStack Query mutations for property field changes.

**Rationale**: Title and description are text fields where continuous typing generates many changes — debounce prevents excessive API calls. Property fields (dropdowns, date pickers) change discretely on selection, so immediate save is appropriate.

**Alternatives considered**:
- Unified debounce for all fields → Rejected: property changes feel laggy with 2s delay
- `useEffect` with setTimeout → Rejected: MobX reaction is the project pattern (per 45-pilot-space-patterns.md)
- Manual save button → Rejected: spec requires auto-save; "no save button" is a project constant

**Implementation**:
- Title/description: MobX observable `dirtyTitle`/`dirtyDescription` → `reaction()` with `delay: 2000` → `useMutation` call
- Properties: Direct `useMutation` on selection change with optimistic update + rollback
- Save indicator: Shared `SaveStatus` component tracking pending/saved/error states per field

---

## R3: Activity Timeline Pagination

**Decision**: Use TanStack Query `useInfiniteQuery` with cursor-based pagination for the activity timeline.

**Rationale**: Cursor pagination is the existing API pattern (per spec assumption #5). `useInfiniteQuery` provides built-in page management, deduplication, and refetch. Infinite scroll via `IntersectionObserver` on a sentinel element.

**Alternatives considered**:
- Offset pagination → Rejected: cursor is more reliable for chronological feeds where new items are inserted
- Load-all approach → Rejected: timelines can grow unbounded; 50-item pages are reasonable
- Virtual scroll (react-window) → Rejected: overkill for 50-item pages; activity entries have variable height

---

## R4: Optimistic Update Strategy

**Decision**: Use TanStack Query `useMutation` with `onMutate` snapshot pattern for all property updates. Title/description use optimistic local state (MobX) with server confirmation.

**Rationale**: TanStack Query's optimistic update pattern (onMutate → snapshot → onError rollback → onSettled invalidate) is the documented project pattern in 45-pilot-space-patterns.md.

**Alternatives considered**:
- Pessimistic updates (wait for server) → Rejected: fails success criterion #8 (100ms feedback)
- MobX-only optimistic (no TanStack) → Rejected: violates state split pattern (API data must be in TanStack Query)

---

## R5: Responsive Layout Strategy

**Decision**: Use Tailwind CSS responsive utilities (`xl:`, `lg:`, `md:`, `sm:`) with CSS flexbox for the split layout. Mobile properties use shadcn/ui `Collapsible` component.

**Rationale**: Tailwind breakpoints align with the spec breakpoints. CSS flexbox with percentage-based widths handles the 70/30 and 65/35 splits. No need for CSS Grid — the layout is a simple two-column split.

**Alternatives considered**:
- CSS Grid → Rejected: unnecessary complexity for two-column layout
- Separate mobile component tree → Rejected: duplication; responsive CSS is sufficient
- Media query hooks (useMediaQuery) → Rejected: Tailwind responsive classes are simpler and avoid hydration mismatch

---

## R6: Comment Edit/Delete UX

**Decision**: Hover-reveal action buttons on own comments. Edit uses inline editor (same TipTap instance). Delete uses confirmation dialog (existing `DeleteConfirmDialog` component).

**Rationale**: Hover-reveal matches Linear/GitHub pattern. Inline editing avoids modal context switch. Reusing `DeleteConfirmDialog` maintains consistency.

**Alternatives considered**:
- Dropdown menu for comment actions → Rejected: adds extra click; hover actions are faster
- Modal editor for comment editing → Rejected: unnecessary context switch for short text
- Soft delete with "undo" toast → Rejected: spec says "confirmation required before deletion"

# UI Design Specification: Feature 017 — Note Versioning & PM Blocks

**Version**: 1.0.0
**Created**: 2026-02-19
**Status**: Draft
**Author**: Designer Agent
**Extends**: `specs/001-pilot-space-mvp/ui-design-spec.md` v4.0 (Section 9 — Note Canvas)
**Depends on**: Feature 016 UI (Ownership gutter, density controls, sidebar panel infrastructure)
**Target**: `frontend/src/features/notes/` + new PM block extensions

---

## Overview

Feature 017 adds two visual systems: (1) version timeline with diff viewer for note history (M6c), and (2) four new PM block types for sprint ceremonies within notes (M6d). These build on the sidebar panel infrastructure and ownership gutter from Feature 016.

**Design Principle**: History is navigable, not buried. PM blocks are living dashboards inside notes, not separate pages.

---

## Component Hierarchy

```
NoteEditor (existing, extended from 016)
├── EditorToolbar (existing)
│   └── VersionButton (NEW — M6c, opens sidebar)
├── TipTap Editor (existing)
│   └── PM Block Extensions (NEW — M6d)
│       ├── SprintBoardBlock
│       ├── DependencyMapBlock
│       ├── CapacityPlanBlock
│       └── ReleaseNotesBlock
├── SidebarPanels (from Feature 016)
│   └── VersionPanel (NEW — M6c)
│       ├── VersionTimeline
│       ├── VersionDiffViewer
│       └── VersionRestoreConfirm
└── AIInsightBadge (NEW — M6d, overlay on PM blocks)
```

---

## 1. Version Timeline (M6c)

Sidebar panel showing point-in-time note snapshots with navigation.

### Panel Layout

```
+-------------------------------+
| Version History          [x]  |
|-------------------------------|
| [Save Version]                |
|                               |
| TODAY                         |
|                               |
| o  Manual save                |
| |  "Before auth refactor"     |
| |  2:34 PM · You         [pin]|
| |                             |
| o  AI: create-spec (after)    |
| |  "Added 42 blocks"          |
| |  2:30 PM · AI          [pin]|
| |                             |
| o  AI: create-spec (before)   |
| |  2:28 PM · AI               |
| |                             |
| o  Auto-save                  |
| |  2:23 PM · System           |
| |                             |
| YESTERDAY                     |
|                               |
| o  Manual save                |
| |  "Sprint planning draft"    |
| |  4:15 PM · You         [pin]|
| |                             |
| o  Auto-save                  |
|    3:50 PM · System           |
|                               |
| [Load more...]                |
+-------------------------------+
```

### Timeline Specifications

| Property | Value |
|----------|-------|
| Panel Width | 280px (matches annotation/presence panels) |
| Panel Position | Right sidebar, toggled from toolbar or density controls |
| Header | `text-lg` (17px), `font-medium`, close button (X icon, `ghost`) |
| Save Version Button | `outline` variant, full width, `sm` size, "Save Version" with `BookmarkPlus` icon |

### Timeline Entry

| Property | Value |
|----------|-------|
| Connector Line | 2px, `--border` color, vertical between entries |
| Dot | 8px circle, filled, color varies by trigger type |
| Label | `text-sm` (13px), `font-medium`, `--foreground` |
| Sublabel (optional) | `text-sm`, `--foreground-muted`, user-provided label in quotes |
| Timestamp | `text-xs` (11px), `--foreground-muted`, `tabular-nums` |
| Author | `text-xs`, "You" / "AI" / "System" |
| Pin Icon | Lucide `Pin` (14px), `ghost` variant, `--foreground-muted`, fills `--primary` when pinned |
| Entry Height | Auto, min 48px |
| Entry Spacing | 4px between entries |
| Date Group Header | `text-xs`, `uppercase`, `tracking-wider`, `--foreground-muted`, `mt-4`, `mb-2` |

### Trigger Type Colors

| Trigger | Dot Color | Icon |
|---------|-----------|------|
| `manual` | `--primary` (teal) | `Bookmark` (12px) |
| `auto` | `--foreground-muted` (gray) | `Clock` (12px) |
| `ai_before` | `--ai` (dusty blue) | `ChevronRight` (12px) |
| `ai_after` | `--ai` (dusty blue) | `ChevronLeft` (12px) |

### Timeline Interactions

| Action | Behavior |
|--------|----------|
| Click entry | Selects version, highlights in timeline, shows diff button |
| Double-click entry | Opens diff viewer comparing selected to current |
| Click pin | Toggles pin status (FR-075: pinned exempt from cleanup) |
| Hover entry | Shows "Compare" and "Restore" action icons |
| Drag-select two entries | Opens diff viewer comparing the two |

### Selected Entry State

```
+-------------------------------+
| > Manual save            [pin]|  <- highlighted row
|   "Before auth refactor"      |
|   2:34 PM · You               |
|   [Compare to Current] [Restore]|
+-------------------------------+
```

| Property | Value |
|----------|-------|
| Selected Background | `--primary-muted` |
| Selected Border | `border-l-3 --primary` |
| Action Buttons | `ghost` variant, `text-xs`, appear on selection |

### Accessibility

- Timeline: `role="list"`, entries `role="listitem"`
- Selected entry: `aria-selected="true"`
- Pin button: `aria-pressed="true/false"`, `aria-label="Pin version"`
- Save Version: `aria-label="Save manual version snapshot"`
- Date groups: heading `role="heading"`, `aria-level="3"`

---

## 2. Diff Viewer (M6c)

Visual side-by-side comparison of two note versions.

### Layout

```
+----------------------------------------------------------+
| Comparing Versions                               [x]     |
|----------------------------------------------------------|
| v1: 2:28 PM (before AI)    |  v2: 2:30 PM (after AI)    |
|                             |                             |
| # Auth Refactor             | # Auth Refactor             |
|                             |                             |
| We need to rethink...       | We need to rethink...       |
|                             |                             |
|                             | + ## AI Analysis            |
|                             | + Based on the requirements |
|                             | + - Consider OAuth PKCE     |
|                             | + - Browser-only for MVP    |
|                             |                             |
| ## Key Problems             | ## Key Problems             |
| - Password reset confusing  | - Password reset confusing  |
| - Social login fails        | - Social login issues       |
|                             |   (renamed)                 |
+----------------------------------------------------------+
| [Restore v1]  AI Digest: "Added analysis section,        |
|               renamed 'fails' to 'issues'"     [Restore v2]|
+----------------------------------------------------------+
```

### Specifications

| Property | Value |
|----------|-------|
| Container | Full sidebar width (280px) or modal for full-screen diff |
| Mode | Side-by-side (default) or unified (toggle) |
| Header | Version labels with timestamps, `text-sm`, `font-medium` |
| Divider | 1px vertical `--border` between sides |
| Added Lines | `bg` green at 10% (`#29A38618`), `+` prefix in `--primary` |
| Removed Lines | `bg` red at 10% (`#D9534F18`), `-` prefix in `#D9534F` |
| Modified Lines | `bg` amber at 10% (`#D9853F18`), text diff highlighted inline |
| Unchanged Lines | Default `bg-background`, `--foreground-muted` |
| Line Numbers | `text-xs`, `tabular-nums`, `--foreground-muted`, 32px gutter |
| Scroll | Synchronized scroll between sides |

### AI Digest (FR-040)

| Property | Value |
|----------|-------|
| Position | Bottom of diff viewer, full width |
| Container | `bg-ai-muted`, `border-t` (`--ai-border`), `p-3` |
| Label | "AI Digest:" prefix, `text-xs`, `font-medium`, `--ai` color |
| Text | `text-sm`, `--foreground`, max 3 lines |
| Loading | Skeleton shimmer while generating (< 3s per FR-040) |
| Error | "Summary unavailable" with [Retry] link |

### Full-Screen Modal Mode

For detailed review, diff viewer can expand to a full-screen modal:

| Property | Value |
|----------|-------|
| Trigger | "Expand" icon button in diff header |
| Modal | Full viewport, frosted glass overlay, `rounded-xl` |
| Side-by-side width | 50/50 split |
| Navigation | Arrow keys or buttons to step through changes |
| Close | X button, Escape key |

### Accessibility

- Diff viewer: `role="region"`, `aria-label="Version comparison"`
- Added/removed indicators: `aria-label="Added line"` / `aria-label="Removed line"`
- Synchronized scroll: announced via `aria-live="off"` (visual only)
- AI digest: `role="note"`, `aria-label="AI change summary"`

---

## 3. Sprint Board Block (M6d)

TipTap NodeView rendering a 6-lane Kanban board within a note.

### Layout

```
+----------------------------------------------------------+
| [layout-dashboard] Sprint Board: Sprint 12     [insight]  |
|----------------------------------------------------------|
| Backlog | Todo  | In Prog | Review | Done   | Cancelled  |
|   (5)   | (3)   |  (4)    |  (2)   | (8)    |   (1)     |
|---------|-------|---------|--------|--------|------------|
| [card]  |[card] | [card]  |[card]  |[card]  | [card]    |
| [card]  |[card] | [card]  |[card]  |[card]  |            |
| [card]  |[card] | [card]  |        |[card]  |            |
| [card]  |       | [card]  |        |[card]  |            |
| [card]  |       |         |        |[card]  |            |
|         |       |         |        |[card]  |            |
|         |       |         |        |[card]  |            |
|         |       |         |        |[card]  |            |
+----------------------------------------------------------+
```

### Specifications

| Property | Value |
|----------|-------|
| Block Type | `sprint-board` (TipTap NodeView) |
| Container | `rounded-lg` (14px), `border` (`--border`), `bg-background`, full editor width |
| Header | `text-lg` (17px), `font-medium`, `LayoutDashboard` icon (18px), cycle name |
| Min Height | 300px |
| Max Height | 600px (scrollable within block) |
| Column Width | Equal distribution (flex: 1), min 120px |
| Column Header | `text-xs`, `uppercase`, `tracking-wider`, count badge in parentheses |
| Column Color | Matches issue state colors (from design system) |

### Issue Mini-Card (within sprint board)

```
+-------------------+
| PS-123       [!!] |
| Fix login bug     |
| [bug] [P: High]   |
| [avatar]          |
+-------------------+
```

| Property | Value |
|----------|-------|
| Card | `rounded` (10px), `border`, `bg-background`, `p-2`, `shadow-sm` |
| Identifier | `text-xs`, `font-mono`, `--foreground-muted` |
| Title | `text-sm`, `font-medium`, max 2 lines, truncated |
| Labels | Pill badges, `text-xs`, colored dots |
| Priority | Vertical bars indicator (from design system) |
| Assignee | 20px avatar, bottom-right |
| Drag Handle | Visible on hover, left edge |

### Drag and Drop

| Property | Value |
|----------|-------|
| Library | dnd-kit (existing) |
| Drag Preview | Ghost card at 80% opacity, slight rotation (2deg) |
| Drop Zone | Column highlight with dashed border, `--primary` at 20% |
| Transition | Card slides to new position, 200ms ease-out |
| AI Transition | When AI proposes a move, card has `--ai` border glow, [Approve] [Reject] overlay |

### AI-Proposed Transitions (FR-050)

```
+-------------------+
| PS-123            |
| Fix login bug     |
| [AI suggests: →]  |
| Move to Done?     |
| [Approve] [Reject]|
+-------------------+
```

| Property | Value |
|----------|-------|
| Overlay | Semi-transparent `--ai-muted` background over card |
| Arrow | Animated arrow icon pointing to target column |
| Buttons | `sm` size, `default` (Approve) / `outline` (Reject) |
| Timeout | Follows approval timeout from Feature 015 |

### Read-Only Fallback (FR-060)

When CRDT is unavailable (Feature 016 gate failure):

| Property | Value |
|----------|-------|
| Visual | Same layout, but no drag handles |
| Badge | "Read-only" badge in header, `secondary` variant |
| Interaction | Click card opens issue detail page (navigation) |

### Accessibility

- Board: `role="region"`, `aria-label="Sprint board: {cycle name}"`
- Columns: `role="list"`, `aria-label="{state} ({count} issues)"`
- Cards: `role="listitem"`, `aria-label="{identifier}: {title}"`
- Drag: `aria-roledescription="draggable"`, keyboard drag via Space + Arrow keys
- AI transition: `aria-live="polite"` announcement of proposed move

---

## 4. Dependency Map Block (M6d)

TipTap NodeView rendering a directed acyclic graph (DAG) of issue dependencies.

### Layout

```
+----------------------------------------------------------+
| [git-branch] Dependency Map: Sprint 12         [insight]  |
|----------------------------------------------------------|
|                                                          |
|   [PS-101] ──────────> [PS-103] ──> [PS-105]            |
|        \                  ^                               |
|         \                 |                               |
|          └──> [PS-102] ──┘                               |
|                  |                                        |
|                  └──────────────> [PS-104]                |
|                                                          |
|   Legend: ── dependency  ═══ critical path                |
|   [zoom +] [zoom -] [fit] [reset]                        |
+----------------------------------------------------------+
```

### Specifications

| Property | Value |
|----------|-------|
| Block Type | `dependency-map` (TipTap NodeView) |
| Container | `rounded-lg` (14px), `border`, `bg-background`, full editor width |
| Header | `text-lg`, `font-medium`, `GitBranch` icon (18px) |
| Canvas | SVG-based rendering, min-height 250px, max-height 500px |
| Layout Algorithm | Dagre (layered graph layout) or similar DAG layouter |

### Node Rendering

```
+-------------------+
| ● PS-103          |
| Implement OAuth   |
| [In Progress]     |
+-------------------+
```

| Property | Value |
|----------|-------|
| Node | `rounded` (10px), `border`, `bg-background`, `shadow-sm`, 140px x 60px |
| State Dot | 8px, matches issue state color |
| Identifier | `text-xs`, `font-mono` |
| Title | `text-xs`, max 2 lines, truncated |
| State Badge | `text-xs`, colored per state |
| Hover | Elevated shadow, shows full title tooltip |
| Click | Opens issue detail in side panel or new tab |

### Edge Rendering

| Type | Style |
|------|-------|
| Normal dependency | 1.5px solid `--border`, arrow at target end |
| Critical path | 3px solid `#D9853F` (amber), arrow at target end |
| Circular (error) | 2px dashed `#D9534F` (red), warning icon overlay |

### Controls

| Control | Icon | Behavior |
|---------|------|----------|
| Zoom In | `ZoomIn` | Scale +25%, max 200% |
| Zoom Out | `ZoomOut` | Scale -25%, min 25% |
| Fit to View | `Maximize2` | Auto-scale to fit all nodes in viewport |
| Reset | `RotateCcw` | Reset to default zoom and position |

| Property | Value |
|----------|-------|
| Control Bar | Bottom-left of canvas, `bg-background/80`, `rounded`, `shadow-sm`, horizontal layout |
| Button Size | `icon-sm` (32px), `ghost` variant |
| Pan | Click and drag canvas (cursor: `grab` / `grabbing`) |
| Zoom | Mouse wheel or pinch gesture |

### Circular Dependency Warning

```
+----------------------------------------------------------+
| [alert-triangle] Circular dependency detected             |
| PS-102 → PS-103 → PS-102                                 |
| Displaying non-cyclic subgraph only.                      |
+----------------------------------------------------------+
```

| Property | Value |
|----------|-------|
| Banner | `bg` amber at 10%, `border` amber, `rounded`, `p-3` |
| Icon | `AlertTriangle` (16px), `#D9853F` |
| Text | `text-sm`, `--foreground` |

### Accessibility

- Graph: `role="img"`, `aria-label="Dependency map: {N} issues, {M} dependencies"`
- Supplementary: Hidden table listing all dependencies for screen readers
- Nodes: focusable, `aria-label="{identifier}: {title}, {state}"`
- Controls: `aria-label` on each button
- Pan/zoom: keyboard accessible via arrow keys (pan) and +/- (zoom)

---

## 5. Capacity Plan Block (M6d)

TipTap NodeView rendering available vs committed hours per team member.

### Layout

```
+----------------------------------------------------------+
| [users] Capacity Plan: Sprint 12               [insight]  |
|----------------------------------------------------------|
|                                                          |
| Sarah K.   [████████████░░░░░░] 32/40h                   |
| Mike R.    [████████████████░░] 36/40h                   |
| You        [██████████████████] 40/40h  ⚠ Over-allocated |
| Alex T.    [████████░░░░░░░░░░] 20/40h                   |
|                                                          |
| Team Total: 128/160h (80%)                                |
+----------------------------------------------------------+
```

### Specifications

| Property | Value |
|----------|-------|
| Block Type | `capacity-plan` (TipTap NodeView) |
| Container | `rounded-lg` (14px), `border`, `bg-background`, full editor width |
| Header | `text-lg`, `font-medium`, `Users` icon (18px) |

### Member Row

| Property | Value |
|----------|-------|
| Row Height | 40px |
| Avatar | 24px circle, left |
| Name | `text-sm`, `font-medium`, 120px fixed width |
| Bar | `rounded-full`, 6px height, flex-1 |
| Bar Fill | `--primary` when < 90%, `#D9853F` at 90-100%, `#D9534F` at >100% |
| Bar Background | `--border` |
| Hours Label | `text-xs`, `tabular-nums`, `--foreground-muted`, right-aligned, 60px |
| Warning | `AlertTriangle` (12px, `#D9534F`) when >100% allocated |

### Team Summary

| Property | Value |
|----------|-------|
| Position | Bottom of block, full width |
| Container | `border-t`, `pt-2`, `mt-2` |
| Text | `text-sm`, `font-medium` |
| Percentage | `tabular-nums`, color coded same as bars |

### No Data State

```
+----------------------------------------------------------+
| [users] Capacity Plan                                     |
|----------------------------------------------------------|
| No team members have weekly_available_hours set.          |
| Go to Settings > Members to configure availability.       |
| [Open Settings]                                           |
+----------------------------------------------------------+
```

### Accessibility

- Chart: `role="table"`, rows `role="row"`, cells `role="cell"`
- Bars: `role="progressbar"`, `aria-valuenow`, `aria-valuemax`, `aria-label="{name}: {committed} of {available} hours"`
- Warning: `role="alert"` for over-allocated members

---

## 6. Release Notes Block (M6d)

TipTap NodeView rendering auto-generated release notes from completed issues.

### Layout

```
+----------------------------------------------------------+
| [rocket] Release Notes: v2.1.0                 [insight]  |
|----------------------------------------------------------|
|                                                          |
| FEATURES                                                  |
| • PS-201 OAuth login with Google and GitHub               |
| • PS-205 Session timeout extended to 24h                  |
|                                                          |
| BUG FIXES                                                 |
| • PS-198 Password reset email not sending                 |
| • PS-199 Social login silent failure                      |
|                                                          |
| IMPROVEMENTS                                              |
| • PS-203 Login page load time reduced by 40%             |
|                                                          |
| INTERNAL                                                  |
| • PS-204 Migrated auth service to new SDK                |
|                                                          |
| [Regenerate]  [Edit]                    AI-classified      |
+----------------------------------------------------------+
```

### Specifications

| Property | Value |
|----------|-------|
| Block Type | `release-notes` (TipTap NodeView) |
| Container | `rounded-lg` (14px), `border`, `bg-background`, full editor width |
| Header | `text-lg`, `font-medium`, `Rocket` icon (18px), version label |

### Classification Categories

| Category | Badge Color | Description |
|----------|-------------|-------------|
| Features | `--primary` (teal) | New functionality |
| Bug Fixes | `#D9534F` (red) | Resolved defects |
| Improvements | `#5B8FC9` (blue) | Enhanced existing |
| Internal | `--foreground-muted` (gray) | Non-user-facing |
| Uncategorized | `#D9853F` (amber) | Low confidence (<30%) |

### Entry Row

| Property | Value |
|----------|-------|
| Bullet | `•`, color matches category |
| Identifier | `text-sm`, `font-mono`, `--foreground-muted`, clickable link |
| Title | `text-sm`, `--foreground` |
| Row Height | Auto, min 24px |
| Human Edits | Preserved with visual indicator: small `user` icon (10px) next to manually edited entries (FR-055) |

### Actions

| Button | Variant | Behavior |
|--------|---------|----------|
| Regenerate | `ai` variant, `sm` | Re-runs classification, preserves human edits |
| Edit | `outline`, `sm` | Makes block content editable (converts to rich text temporarily) |
| AI-classified | `text-xs`, `--ai` color, informational label |

### Accessibility

- Block: `role="region"`, `aria-label="Release notes: {version}"`
- Categories: `role="list"`, `aria-label="{category} ({count} items)"`
- Entries: `role="listitem"`, `aria-label="{identifier}: {title}"`

---

## 7. AI Insight Badges (M6d)

Floating badges on PM blocks indicating AI analysis status.

### Layout

```
+----------------------------------------------------------+
| [layout-dashboard] Sprint Board: Sprint 12  [🟢 On Track]|
+----------------------------------------------------------+
```

### Badge Specifications

| Level | Color | Background | Icon | Example Label |
|-------|-------|------------|------|---------------|
| Green | `#29A386` | `#29A38618` | `CheckCircle` (12px) | "On Track" |
| Yellow | `#D9853F` | `#D9853F18` | `AlertTriangle` (12px) | "At Risk" |
| Red | `#D9534F` | `#D9534F18` | `AlertOctagon` (12px) | "Blocked" |
| Gray | `--foreground-muted` | `--background-subtle` | `Info` (12px) | "Insufficient Data" |

### Badge Position and Style

| Property | Value |
|----------|-------|
| Position | Header row of PM block, right-aligned before insight icon |
| Size | `text-xs` (11px), `px-2`, `py-0.5`, `rounded-full` |
| Icon | 12px, left of text |
| Spacing | 4px gap between icon and text |
| Hover | Shows tooltip with analysis details |
| Click | Expands insight panel below header |

### Insight Tooltip

```
+-------------------------------+
| Sprint 12 Analysis            |
|-------------------------------|
| Velocity: 32 pts (avg: 28)   |
| Completion: 65% (day 7/10)   |
| Blockers: 2 issues            |
|                               |
| "Team is ahead of average     |
|  velocity. Two blockers need  |
|  attention by mid-sprint."    |
|                               |
| References:                   |
| PS-201, PS-203 (blocked)      |
|                               |
| [Dismiss]                     |
+-------------------------------+
```

| Property | Value |
|----------|-------|
| Width | 280px |
| Position | Below badge, right-aligned |
| Background | `bg-background`, `shadow-md`, `rounded-lg`, `border` |
| Metrics | `text-sm`, `font-medium`, `tabular-nums` |
| AI Text | `text-sm`, `--foreground-muted`, italic |
| References | `text-xs`, `font-mono`, `--primary`, clickable |
| Dismiss | `ghost`, `text-xs` (FR-059) |

### Insufficient Data State (FR-058)

When <3 sprints of historical data:

| Property | Value |
|----------|-------|
| Badge | Gray, "Insufficient Data" |
| Tooltip | "AI insights require at least 3 completed sprints. Current: {N}." |
| No Dismiss | Badge stays as informational indicator |

### Accessibility

- Badge: `role="status"`, `aria-label="AI insight: {level} - {label}"`
- Tooltip: `role="tooltip"`, triggered by hover and focus
- Dismiss: `aria-label="Dismiss AI insight"`

---

## Responsive Behavior

### Version Timeline

| Breakpoint | Behavior |
|------------|----------|
| Desktop (>1280px) | Sidebar panel (280px) |
| Tablet (768–1279px) | Overlay panel, slides from right |
| Mobile (<768px) | Full-screen modal |

### Diff Viewer

| Breakpoint | Behavior |
|------------|----------|
| Desktop (>1280px) | Side-by-side in sidebar or modal |
| Tablet (768–1279px) | Unified diff (single column) |
| Mobile (<768px) | Unified diff, full-screen modal |

### Sprint Board

| Breakpoint | Behavior |
|------------|----------|
| Desktop (>1280px) | 6 columns visible, horizontal scroll if needed |
| Tablet (768–1279px) | 3 columns visible, swipe/scroll for more |
| Mobile (<768px) | Single column view, vertical stack with state tabs |

### Dependency Map

| Breakpoint | Behavior |
|------------|----------|
| Desktop (>1280px) | Full graph visible, zoom controls |
| Tablet (768–1279px) | Horizontal scroll, pinch-to-zoom |
| Mobile (<768px) | Simplified list view (no graph), ordered by critical path |

### Capacity Plan

| Breakpoint | Behavior |
|------------|----------|
| All breakpoints | Responsive within block, bars scale to available width |
| Mobile (<768px) | Name labels stack above bars (2-row layout per member) |

### Release Notes

| Breakpoint | Behavior |
|------------|----------|
| All breakpoints | Naturally responsive (text content) |
| Mobile (<768px) | Categories collapse to expandable sections |

---

## Animation & Transitions

| Animation | Duration | Easing | Trigger |
|-----------|----------|--------|---------|
| Version panel slide | 200ms | ease-out | Toggle from toolbar |
| Timeline entry appear | 150ms | ease-out | New version created |
| Diff highlight | 300ms | ease-out | Entering diff viewer |
| Sprint card drag | native dnd-kit | -- | Drag start |
| Sprint card drop | 200ms | ease-out | Drop in new column |
| AI transition proposal glow | 1500ms | ease-in-out, infinite | AI-proposed move |
| Dependency map zoom | 200ms | ease-out | Zoom control click |
| Dependency map pan | 16ms (60fps) | linear | Mouse/touch drag |
| Insight badge appear | 300ms | ease-out | Analysis complete |
| Insight tooltip | 150ms | ease-out | Hover/focus |
| Capacity bar fill | 400ms | ease-out | Data load |

### Reduced Motion

- Drag: no rotation on preview, instant position
- Zoom/pan: instant changes
- Glow animation: static border color
- Bar fill: instant width
- All fades: instant opacity

---

## Dark Mode

All components use CSS custom properties. Dark mode adjustments:

| Element | Light Mode | Dark Mode |
|---------|------------|-----------|
| PM block container bg | `--background` | `--background` |
| Sprint card bg | `--background` | `--background` (slightly elevated) |
| Dependency node bg | `--background` | `--background` |
| Edge lines | `--border` | `--border` (higher opacity for visibility) |
| Critical path edge | `#D9853F` | `#D9853F` (same — high contrast) |
| Diff added bg | `#29A38618` | `#29A38625` (slightly stronger) |
| Diff removed bg | `#D9534F18` | `#D9534F25` (slightly stronger) |
| Version timeline line | `--border` | `--border` |

---

## Implementation Notes

### File Organization

```
features/notes/editor/extensions/pm-blocks/
├── sprint-board/
│   ├── SprintBoardBlock.tsx           (NEW)
│   ├── SprintBoardMiniCard.tsx        (NEW)
│   ├── SprintBoardColumn.tsx          (NEW)
│   └── __tests__/
├── dependency-map/
│   ├── DependencyMapBlock.tsx         (NEW)
│   ├── DependencyNode.tsx             (NEW)
│   ├── DependencyEdge.tsx             (NEW)
│   ├── DependencyControls.tsx         (NEW)
│   └── __tests__/
├── capacity-plan/
│   ├── CapacityPlanBlock.tsx          (NEW)
│   ├── CapacityMemberRow.tsx          (NEW)
│   └── __tests__/
├── release-notes/
│   ├── ReleaseNotesBlock.tsx          (NEW)
│   ├── ReleaseCategory.tsx            (NEW)
│   └── __tests__/
├── shared/
│   ├── AIInsightBadge.tsx             (NEW)
│   ├── AIInsightTooltip.tsx           (NEW)
│   └── PMBlockHeader.tsx              (NEW, shared header pattern)
features/notes/components/
├── VersionPanel.tsx                   (NEW)
├── VersionTimeline.tsx                (NEW)
├── VersionDiffViewer.tsx              (NEW)
├── VersionRestoreConfirm.tsx          (NEW)
```

### Store Integration

| Component | Store | Observable |
|-----------|-------|-----------|
| VersionPanel | VersionStore (new) | `versions`, `selectedVersion`, `diffResult` |
| VersionTimeline | VersionStore | `versions` (sorted list), `pinnedVersions` |
| SprintBoardBlock | Block data (TipTap node attrs) + IssueStore (existing) | Issue data fetched via TanStack Query |
| DependencyMapBlock | Block data + IssueStore | `issueRelations` |
| CapacityPlanBlock | Block data + WorkspaceStore (existing) | `members`, `memberCapacity` |
| ReleaseNotesBlock | Block data + IssueStore | `completedIssues` for cycle |
| AIInsightBadge | InsightStore (new) | `insights` (Map<blockId, PMBlockInsight>) |

### TipTap Extension Registration

All four PM blocks register as TipTap NodeView extensions via the existing `createEditorExtensions()` factory. They follow the same pattern as the 6 existing PM block types (decision, form, raci, risk, timeline, dashboard).

### Dependencies

- `dagre` or `@dagrejs/dagre` — DAG layout for dependency map
- `dnd-kit` (existing) — drag and drop for sprint board
- No new backend dependencies for version UI (API calls to existing version endpoints)
- Recharts (existing) — not needed; capacity plan uses simple HTML/CSS bars

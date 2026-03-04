# UI Design Specification: Knowledge Graph Feature

**Version**: 1.0.0
**Created**: 2026-03-03
**Status**: Approved — implementation target
**Parent spec**: `specs/001-pilot-space-mvp/ui-design-spec.md` v4.0
**Feature**: Knowledge Graph exploration embedded in Issue Detail Page

---

## Table of Contents

1. [Design Mood & Principles](#1-design-mood--principles)
2. [Node Type Color Palette](#2-node-type-color-palette)
3. [Design Tokens](#3-design-tokens)
4. [Mini-Graph Component Spec](#4-mini-graph-component-spec)
5. [Full Graph Component Spec](#5-full-graph-component-spec)
6. [GitHub Implementation Section Spec](#6-github-implementation-section-spec)
7. [Right Panel Tab Bar Spec](#7-right-panel-tab-bar-spec)
8. [Interaction Flow Diagrams](#8-interaction-flow-diagrams)
9. [Accessibility Requirements](#9-accessibility-requirements)
10. [Loading, Error, and Empty States](#10-loading-error-and-empty-states)

---

## 1. Design Mood & Principles

### Visual Identity

The knowledge graph is **connective tissue, not decoration**. It surfaces existing relationships that have always been implicit — decisions that led to issues, conversations that produced patterns, code references that tie PRs to discussions. The visual language reinforces this:

- **Technical but approachable**: The graph reads like a Linear issue board that gained spatial awareness. No neon gradients. No "startup demo" aesthetics. Understated geometry.
- **Clarity over density**: At most 50 nodes visible at once. Nodes are labeled, not just colored. Relationships are explained with edge labels on hover.
- **Graph as navigator**: The graph is not a visualization for its own sake — every node and edge is a navigation target. Clicking a node opens details; double-clicking expands context.

### Design Principles

| Principle | Application |
|-----------|-------------|
| **Progressive disclosure** | Mini-graph (200px, read-only) → Full graph (interactive). Complexity revealed on demand. |
| **Preserve context** | Chat is hidden (CSS), not unmounted, when Graph tab is active. Conversation state survives tab switches. |
| **AI contributions labeled** | AI-generated nodes (LearnedPattern, SkillOutcome, ConversationSummary) always have an AI indicator chip. Human-created nodes (Issue, Note, Decision) do not. |
| **Consistent with Linear** | Same `CollapsibleSection` pattern, same `shadcn/ui` primitives, same Tailwind spacing scale. |
| **Reduced motion respect** | All force-directed animation disabled when `prefers-reduced-motion: reduce`. Static layout renders immediately. |

### Motion Design

| Animation | Duration | Easing | Reduced Motion |
|-----------|----------|--------|----------------|
| Tab switch (Chat ↔ Graph) | 200ms | `ease-in-out` | instant |
| Force layout settle | 800ms | custom spring | skip (render final position) |
| Node hover state | 150ms | `ease-out` | instant |
| Node selection ring | 200ms | `ease-in-out` | instant |
| Highlight pulse (from implementation panel) | 1.5s loop, 3 iterations | `ease-in-out` | single flash |
| Detail panel slide-in | 200ms | `ease-out` | instant |
| Collapsible section expand | 150ms | `ease-out` | instant |

### Information Density Guidelines

- **Node labels**: Truncated at 20 chars with ellipsis. Full label in tooltip.
- **Edge labels**: Hidden by default for weak edges (<0.3 weight). Shown on hover for all edges. Always shown for strong edges (≥0.7 weight).
- **Mini-graph**: 2-letter abbreviations only (IS, NO, DE, PR, CR, LP, US, CO, CY, WI, CS, SO). No text labels. Tooltip on hover.
- **Full graph**: Short labels visible at normal zoom. At zoom < 0.5×, labels hidden, tooltip only.

---

## 2. Node Type Color Palette

### Definition

All colors defined as Tailwind classes and CSS custom properties. Dark mode variants shift 1-2 steps lighter for sufficient contrast on dark canvas backgrounds.

| Node Type | Light Mode | Dark Mode | Tailwind Class | Mini Abbrev | Lucide Icon | Shape |
|-----------|------------|-----------|----------------|-------------|-------------|-------|
| Issue (current — focal node) | `blue-600` + ring | `blue-400` + ring | `text-blue-600 dark:text-blue-400` | IS | `CircleDot` | Rounded rect (larger: 48×32) |
| Issue (other) | `blue-500` | `blue-400` | `text-blue-500 dark:text-blue-400` | IS | `CircleDot` | Rounded rect (40×28) |
| Note | `emerald-500` | `emerald-400` | `text-emerald-500 dark:text-emerald-400` | NO | `FileText` | Rounded rect (40×28) |
| Decision | `amber-500` | `amber-400` | `text-amber-500 dark:text-amber-400` | DE | `Scale` | Diamond (36×36) |
| User | `slate-400` | `slate-300` | `text-slate-400 dark:text-slate-300` | US | `User` | Circle (32×32) |
| Pull Request | `purple-500` | `purple-400` | `text-purple-500 dark:text-purple-400` | PR | `GitPullRequest` | Rounded rect (40×28) |
| Branch | `purple-300` | `purple-200` | `text-purple-300 dark:text-purple-200` | BR | `GitBranch` | Rounded rect (40×28) |
| Commit | `purple-200` | `purple-100` | `text-purple-200 dark:text-purple-100` | CO | `GitCommit` | Circle (28×28) |
| Code Reference | `orange-500` | `orange-400` | `text-orange-500 dark:text-orange-400` | CR | `Code` | Rounded rect (40×28) |
| Learned Pattern | `teal-500` | `teal-400` | `text-teal-500 dark:text-teal-400` | LP | `Lightbulb` | Hexagon (36×36) |
| Conversation Summary | `slate-300` | `slate-200` | `text-slate-300 dark:text-slate-200` | CS | `MessageSquare` | Rounded rect (40×28) |
| Skill Outcome | `indigo-400` | `indigo-300` | `text-indigo-400 dark:text-indigo-300` | SO | `Sparkles` | Rounded rect (40×28) |
| Work Intent | `violet-400` | `violet-300` | `text-violet-400 dark:text-violet-300` | WI | `Target` | Rounded rect (40×28) |
| User Preference | `slate-400` | `slate-300` | `text-slate-400 dark:text-slate-300` | UP | `Heart` | Circle (28×28) |

### Contrast Verification

All node colors meet WCAG 2.1 AA (4.5:1 contrast ratio) when rendered as colored borders/strokes on `bg-background` (white light / dark gray dark). Filled node backgrounds use `bg-{color}-500/10` with a `border-{color}-500` ring — text inside nodes is always `text-foreground`.

### AI-Generated Node Indicator

Nodes with `node_type` in `[skill_outcome, conversation_summary, learned_pattern, work_intent]` render a small `Sparkles` icon badge at top-right corner of the node. Size: 10×10px, `text-muted-foreground`. Not rendered in mini-graph.

---

## 3. Design Tokens

```css
/* ============================================
   Knowledge Graph Design Tokens
   Add to: frontend/src/styles/globals.css
   ============================================ */

:root {
  /* Node type colors — light mode */
  --graph-node-issue-current: theme(colors.blue.600);   /* focal issue */
  --graph-node-issue:         theme(colors.blue.500);
  --graph-node-note:          theme(colors.emerald.500);
  --graph-node-decision:      theme(colors.amber.500);
  --graph-node-user:          theme(colors.slate.400);
  --graph-node-pr:            theme(colors.purple.500);
  --graph-node-branch:        theme(colors.purple.300);
  --graph-node-commit:        theme(colors.purple.200);
  --graph-node-code-ref:      theme(colors.orange.500);
  --graph-node-pattern:       theme(colors.teal.500);
  --graph-node-summary:       theme(colors.slate.300);
  --graph-node-skill:         theme(colors.indigo.400);
  --graph-node-intent:        theme(colors.violet.400);
  --graph-node-preference:    theme(colors.slate.400);

  /* Edge styles */
  --graph-edge-strong:        theme(colors.foreground / 0.6);  /* weight >= 0.7 */
  --graph-edge-medium:        theme(colors.foreground / 0.3);  /* weight 0.3–0.7 */
  --graph-edge-weak:          theme(colors.foreground / 0.12); /* weight < 0.3 */

  /* Graph canvas */
  --graph-bg:                 theme(colors.background);
  --graph-grid:               theme(colors.muted / 0.3);        /* subtle dot grid */
  --graph-canvas-border:      theme(colors.border);

  /* Current issue node glow */
  --graph-node-current-glow:  0 0 0 2px theme(colors.blue.600),
                              0 0 16px theme(colors.blue.600 / 0.3);

  /* Highlight pulse (from implementation panel click) */
  --graph-highlight-color:    theme(colors.blue.400);

  /* Animation durations */
  --graph-settle-duration:    800ms;
  --graph-highlight-pulse:    1.5s;
  --graph-tab-transition:     200ms;
  --graph-node-hover:         150ms;
  --graph-detail-slide:       200ms;
}

.dark {
  /* Node type colors — dark mode (1-2 steps lighter) */
  --graph-node-issue-current: theme(colors.blue.400);
  --graph-node-issue:         theme(colors.blue.400);
  --graph-node-note:          theme(colors.emerald.400);
  --graph-node-decision:      theme(colors.amber.400);
  --graph-node-user:          theme(colors.slate.300);
  --graph-node-pr:            theme(colors.purple.400);
  --graph-node-branch:        theme(colors.purple.200);
  --graph-node-commit:        theme(colors.purple.100);
  --graph-node-code-ref:      theme(colors.orange.400);
  --graph-node-pattern:       theme(colors.teal.400);
  --graph-node-summary:       theme(colors.slate.200);
  --graph-node-skill:         theme(colors.indigo.300);
  --graph-node-intent:        theme(colors.violet.300);
  --graph-node-preference:    theme(colors.slate.300);
}

/* Reduced motion overrides */
@media (prefers-reduced-motion: reduce) {
  --graph-settle-duration:  0ms;
  --graph-highlight-pulse:  0ms;
  --graph-tab-transition:   0ms;
  --graph-node-hover:       0ms;
  --graph-detail-slide:     0ms;
}

/* Highlight pulse keyframe */
@keyframes graph-highlight-pulse {
  0%   { box-shadow: 0 0 0 2px var(--graph-highlight-color); }
  50%  { box-shadow: 0 0 0 6px var(--graph-highlight-color), 0 0 24px color-mix(in srgb, var(--graph-highlight-color) 40%, transparent); }
  100% { box-shadow: 0 0 0 2px var(--graph-highlight-color); }
}
```

---

## 4. Mini-Graph Component Spec

### Overview

`IssueKnowledgeGraphMini` renders inside a `CollapsibleSection` in the left editor column. It is a compact, read-only preview of the issue's knowledge graph. Its purpose is discoverability — the user sees connections exist, then clicks "Expand full view" to explore them.

### Dimensions and Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ CollapsibleSection header                                        │
│   🕸 Knowledge Graph (12 nodes)    [chevron icon]               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │                                                        │     │
│  │   ● IS  ── ● NO   ● DE                                │     │
│  │    ↓           ╲                                      │     │
│  │   ● PR        ● US     ● CR                           │     │
│  │        ──  ● LP  ── ● SO                              │     │
│  │                                                        │     │
│  └────────────────────────────────────────────────────────┘     │
│  [Expand full view →]                                            │
└─────────────────────────────────────────────────────────────────┘
```

| Property | Value |
|----------|-------|
| Section wrapper | `CollapsibleSection` with icon `Network` (Lucide) |
| Graph container height | `200px` fixed |
| Graph container width | `100%` of editor column |
| Graph container border | `1px solid border` with `rounded-lg` |
| Graph background | `bg-muted/30` |
| Node size | 20px diameter circles |
| Node color | Filled circle using node type color token, 80% opacity |
| Node label | 2-letter abbreviation, `text-[9px]`, `font-medium`, `text-white` |
| Edge color | `--graph-edge-medium` (`hsl(var(--foreground) / 0.3)`) |
| Edge width | 1px |
| Layout | Static force-directed — computed once on data load, no animation |
| Interactions | Hover tooltip only (Radix `Tooltip` — node type + label, max 40 chars) |
| Pan/zoom | Disabled |

### "Expand Full View" Button

```
[Expand full view →]
```

- Placement: Below the graph container, right-aligned
- Style: `Button` variant `ghost`, size `sm`, `text-muted-foreground hover:text-foreground`
- Icon: `Maximize2` (Lucide), 14px, before text
- Action: Calls `onExpandFullView()` → switches right panel to "knowledge-graph" tab
- If panel is already on "knowledge-graph" tab: button label changes to "View in graph panel ↗"

### Node Count Badge

Shown in the `CollapsibleSection` header count badge (same as existing Relationships, GitHub sections):
- Count: total nodes in the subgraph
- Format: `Knowledge Graph ({n} nodes)`
- If no data yet: `Knowledge Graph`

### Empty State (Mini)

```
┌────────────────────────────────────────────────────────┐
│                                                        │
│                  ◇ ── ○                               │
│                                                        │
│         No graph data yet.                             │
│    Use AI chat to build connections.                   │
│                                                        │
└────────────────────────────────────────────────────────┘
```

- Simple SVG illustration (3 geometric shapes with connecting lines)
- `text-muted-foreground text-xs text-center`
- No "Expand full view" button in empty state

### Dark Mode

Graph container background switches to `bg-muted/20`. Node colors use dark mode tokens. Edge colors auto-adjust via CSS variable.

---

## 5. Full Graph Component Spec

### Overview

`IssueKnowledgeGraphFull` renders in the right panel when "Knowledge Graph" tab is active. Full interactivity: zoom, pan, click to select, double-click to expand, node detail panel.

### Library: `@xyflow/react` (React Flow)

**Chosen over alternatives for these reasons**:

| Factor | React Flow | Why It Wins |
|--------|-----------|-------------|
| Custom node JSX | Full React components | Needed for icons, badges, multi-line labels |
| TypeScript | Excellent, first-class | Required (pyright strict-equivalent) |
| Mini-graph sharing | Same node/edge data format for both views | Reduces data transformation code |
| Built-ins | Minimap, Controls, Background components | All needed features included |
| Bundle | ~45KB gzipped | Lazy-loaded via `React.lazy` — no initial page load cost |
| Force layout | `@xyflow/react` + `d3-force` (separate package) | Acceptable; static positions computed in worker |
| License | MIT | No licensing concern |

### Three-Zone Layout

```
┌──────────────────────────────────────────────┐
│  [← Chat]  Node Type Filters ▾  [Depth: 2]  │  ← Toolbar (44px, border-b)
├──────────────────────────────────────────────┤
│                                              │
│   Interactive force-directed graph           │  ← Canvas (flex-1, overflow hidden)
│   with zoom/pan                              │
│                                              │
│   Current issue node: larger, glow ring      │
│                                              │
│   [+] [-] [⤢]   ┌──────┐  ← Minimap        │
│                  │ mini │    bottom-right     │
│                  └──────┘    80×60px          │
│                                              │
├──────────────────────────────────────────────┤
│  (empty when no node selected)               │  ← Detail Panel (0px collapsed)
│                                              │
│  ┌──────────────────────────────────────────┐│
│  │ PS-38: "Design auth flow"                ││  ← Expanded (200px max)
│  │ 🔵 Issue · Done · High Priority         ││
│  │ Related: PS-42, PS-45                    ││
│  │ [Open Issue →]  [Show neighbors]         ││
│  └──────────────────────────────────────────┘│
└──────────────────────────────────────────────┘
```

### Toolbar

```
┌──────────────────────────────────────────────────────────────────┐
│  ← Chat    [Issues] [Notes] [PRs] [Decisions] [Code] [All]      │
│            Node type filter chips (toggle, multi-select)         │
│                                              Depth: [1] [2] [3] │
└──────────────────────────────────────────────────────────────────┘
```

| Element | Style |
|---------|-------|
| "← Chat" button | `Button` ghost sm, `ArrowLeft` icon, `text-muted-foreground` |
| Filter chips | `Badge` outline variant; active = filled with node type color |
| Depth selector | 3-way toggle: `1`, `2`, `3` hops. `Button` group pattern. |
| Toolbar height | 44px, `border-b border-border`, `bg-background/80 backdrop-blur` |

### Node Component Anatomy

Each node in the full graph is a custom React Flow node component:

```
┌─────────────────────────────┐
│ [Icon] PS-42                │  ← label (truncated at 20 chars)
│        Implement auth flow  │  ← summary line (truncated at 30 chars, text-xs muted)
└─────────────────────────────┘
  │                           │
  └──── border: 2px solid ────┘
         node type color
         selected: 3px ring + shadow
         current issue: glow box-shadow
         highlighted: pulse animation (3 iterations)
         hover: brightness(1.1) + scale(1.02)
```

| State | Visual Treatment |
|-------|-----------------|
| Default | `border-2 border-{nodeColor}`, `bg-{nodeColor}/10` |
| Hover | `border-{nodeColor}` + `scale-[1.02]`, cursor: pointer |
| Selected | `border-3 ring-2 ring-{nodeColor}/40 shadow-md` |
| Current issue | Default + `box-shadow: var(--graph-node-current-glow)` |
| Highlighted | `animation: graph-highlight-pulse 1.5s ease-in-out 3` |
| AI-generated | Small `Sparkles` 10×10 badge top-right corner |

### Edge Component Anatomy

Edges are styled based on weight:

| Weight Range | Line Style | Width | Color Token | Label Visibility |
|-------------|------------|-------|-------------|-----------------|
| ≥ 0.7 (strong) | Solid | 2px | `--graph-edge-strong` | Always shown (center of edge) |
| 0.3–0.7 (medium) | Solid | 1px | `--graph-edge-medium` | On hover only |
| < 0.3 (weak) | Dashed (4,4) | 1px | `--graph-edge-weak` | Hidden; shown if "weak" filter active |

- Directional arrows: `arrowClosed` marker at target end, 8px, same color as edge
- Edge label style: `text-[9px] text-muted-foreground bg-background/90 px-1 rounded`

### Node Detail Panel

```
┌────────────────────────────────────────────────────────────────┐
│ ● [Icon] PS-38  [✕ close]                                      │
│ "Design auth flow"                                             │
│                                                                │
│ [Issue] · Done · High Priority                                 │
│ Created: Feb 20 · Last updated: Mar 1                          │
│ Assigned: Jane Doe                                             │
│                                                                │
│ Related via: relates_to, caused_by                             │
│                                                                │
│ [Open Issue →]  [Expand neighborhood]                          │
└────────────────────────────────────────────────────────────────┘
```

| Property | Value |
|----------|-------|
| Height | Collapsed: 0px; Expanded: max 200px (scrollable if content overflows) |
| Transition | `height 200ms ease-out` |
| Background | `bg-muted/50 border-t border-border` |
| Close button | `✕` top-right, dismisses panel + deselects node |
| "Open Issue →" | Only shown for `issue` and `note` node types. Navigates to detail page. |
| "Expand neighborhood" | Triggers double-click behavior (fetches 1 more hop) |

### Minimap

- Position: Bottom-right of canvas, `inset: 16px`
- Size: 80×60px
- Background: `bg-background border border-border rounded`
- Node representation: colored dots matching node type color
- Viewport indicator: semi-transparent rectangle

### Zoom Controls

- Position: Bottom-left of canvas, `inset: 16px`
- Buttons: `[+]` zoom in, `[-]` zoom out, `[⤢]` fit to screen
- Style: shadcn `Button` icon variant, stacked vertically
- Zoom range: 0.3× minimum, 3× maximum

### Interactions Table

| Action | Behavior |
|--------|----------|
| Hover node | Tooltip: `{label} · {nodeType}\n{summary}` (Radix `Tooltip`, 300ms delay) |
| Click node | Select → show detail panel. Highlight connected edges (opacity 0.2 → 1.0 on connected, 0.1 on others). |
| Double-click node | Fetch 1 more hop neighbors from API (`GET /nodes/{id}/neighbors?depth=1`). Add to graph with settle animation. |
| Click selected node | Deselect → hide detail panel |
| Click canvas background | Deselect any selected node |
| Click issue/note in detail panel "Open →" | Navigate to `/{workspaceSlug}/{type}/{id}` |
| Scroll/pinch | Zoom 0.3×–3× |
| Drag canvas | Pan |
| Drag node | Move node position (React Flow default) |
| `highlightNodeId` prop set | Auto-center on node, pulse animation (3 cycles), open detail panel |
| Keyboard: Tab | Cycle through nodes (focus ring visible) |
| Keyboard: Enter on focused node | Select + open detail panel |
| Keyboard: Escape | Deselect / close detail panel |

---

## 6. GitHub Implementation Section Spec

### Overview

`GitHubImplementationSection` replaces the current `GitHubSection`. It retains all existing GitHub activity display and adds an inline implementation plan panel below it.

### Full ASCII Mockup

```
┌─────────────────────────────────────────────────────────────────┐
│ CollapsibleSection header                                        │
│   ⚡ GitHub & Implementation (3)   [chevron]                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  AREA 1 — GitHub Activity (same as current GitHubSection)       │
│                                                                  │
│  Pull Requests                                                   │
│  ┌───────────────────────────────────────────────┐              │
│  │  ● #87 Add JWT middleware     [merged] [↗]   │              │
│  │  ○ #92 Add RLS policies       [open]   [↗]   │              │
│  └───────────────────────────────────────────────┘              │
│                                                                  │
│  Branches                                                        │
│  ┌───────────────────────────────────────────────┐              │
│  │  ⎇ feat/PS-42-auth-flow           [↗]        │              │
│  └───────────────────────────────────────────────┘              │
│                                                                  │
│  Commits (3 recent)                                              │
│  ┌───────────────────────────────────────────────┐              │
│  │  ◉ "Implement JWT middleware"    Jane · 2d    │              │
│  │  ◉ "Add auth schema migration"   Jane · 3d    │              │
│  │  ◉ "Initial auth module setup"   Jane · 5d    │              │
│  └───────────────────────────────────────────────┘              │
│                                                                  │
│  ────────────────────────────────────────────────               │
│                                                                  │
│  AREA 2 — Implementation Plan (NEW)                             │
│                                                                  │
│  Implementation Plan                       [Regenerate]         │
│                                                                  │
│  Branch: feat/PS-42-auth-flow                                    │
│                                                                  │
│  Tasks                                                           │
│  ┌───────────────────────────────────────────────┐              │
│  │  ☐  1. Design auth schema                     │              │
│  │  ☑  2. Implement JWT middleware               │              │
│  │  ☐  3. Add RLS policies                       │              │
│  │  ☐  4. Write integration tests                │              │
│  └───────────────────────────────────────────────┘              │
│                                                                  │
│  CLI Commands                                                    │
│  ┌───────────────────────────────────────────────┐              │
│  │  pilot implement PS-42               [copy ⎘] │              │
│  │  pilot implement PS-42 --oneshot     [copy ⎘] │              │
│  └───────────────────────────────────────────────┘              │
│                                                                  │
│  Affected Knowledge Graph Nodes                                  │
│  ┌───────────────────────────────────────────────┐              │
│  │  ● auth_module (code_ref)                     │              │
│  │  ● rls_policies (code_ref)                    │              │
│  │  ◆ "Chose Supabase Auth" (decision)           │              │
│  │  ◉ auth-design.md (note)                      │              │
│  └───────────────────────────────────────────────┘              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Area 1: GitHub Activity (Unchanged from Current `GitHubSection`)

All existing behavior preserved:
- PR list with `[merged]` / `[open]` / `[closed]` badges
- Branch list with external link
- Commit list (author name, relative time)
- Empty state: `[Create Branch]` + `[Implement with Claude]` buttons

### Area 2: Implementation Plan

Shown when `ai_contexts` data exists for this issue OR after user clicks `[Generate Plan]`.

#### Task Checklist

```
┌─────────────────────────────────────────────────────────┐
│  ☐  1. Design auth schema                               │
│  ☑  2. Implement JWT middleware                         │
│  ☐  3. Add RLS policies                                 │
└─────────────────────────────────────────────────────────┘
```

- Source: `aiStore.aiContext.tasks_checklist` array
- Checkboxes: read-only (`pointer-events: none`). Visual state only.
- Checked = `text-muted-foreground line-through`, unchecked = `text-foreground`
- Container: `rounded-md border border-border bg-muted/30 p-3 space-y-1`

#### CLI Commands

```
┌─────────────────────────────────────────────────────────┐
│  pilot implement PS-42                       [copy ⎘]  │
│  pilot implement PS-42 --oneshot             [copy ⎘]  │
└─────────────────────────────────────────────────────────┘
```

- Style: `font-mono text-xs bg-muted rounded px-3 py-2`
- Copy button: `Button` ghost xs, `Copy` icon (Lucide), `text-muted-foreground`
- On copy: button flashes `Check` icon for 1.5s, then reverts

#### Affected Knowledge Graph Nodes

```
┌─────────────────────────────────────────────────────────┐
│  ● auth_module (code_ref)                               │
│  ● rls_policies (code_ref)                              │
│  ◆ "Chose Supabase Auth" (decision)                    │
│  ◉ auth-design.md (note)                               │
└─────────────────────────────────────────────────────────┘
```

- Source: `useIssueKnowledgeGraph` hook — nodes connected to the issue within depth 2 that are relevant to the implementation scope (code references, decisions, related notes). Filtered client-side from the graph data.
- Each row is a clickable chip:
  - Hover: `bg-muted/80`
  - Click: calls `onHighlightNode(nodeId)` → parent switches right panel to Graph tab + sets `highlightNodeId`
- Node indicator shape:
  - `●` for node types that use circle shape (User, Commit, UserPreference)
  - `◆` for diamond shapes (Decision)
  - `⬡` for hexagon shapes (LearnedPattern)
  - `▮` for rounded rect shapes (all others)
- Color: uses node type CSS variable

#### Generate/Regenerate Button

- `[Generate Plan]` — shown when no `ai_contexts` data exists. Triggers existing AI context generation flow.
- `[Regenerate]` — shown when data exists. Same action. Style: `Button` ghost sm, right-aligned.

---

## 7. Right Panel Tab Bar Spec

### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  💬 Chat              🔗 Knowledge Graph                     │
│  ───────                                                     │  ← Active indicator: 2px underline
└──────────────────────────────────────────────────────────────┘
```

### Tab Bar Container

| Property | Value |
|----------|-------|
| Height | 40px |
| Border | `border-b border-border` |
| Background | `bg-background` |
| Layout | `flex items-center gap-1 px-2` |

### Individual Tab Button

| State | Style |
|-------|-------|
| Default (inactive) | `text-muted-foreground hover:text-foreground`, no background |
| Active | `text-foreground`, 2px bottom border in `border-foreground` |
| Hover (inactive) | `text-foreground/80`, `bg-muted/50` |
| Focus | `ring-2 ring-offset-1 ring-ring` (keyboard navigation) |

- Padding: `px-3 py-2`
- Icon: 14px, `mr-1.5`
- Font: `text-sm font-medium`
- Icons: `MessageSquare` for Chat, `Network` for Knowledge Graph

### Active Indicator

```css
.tab-active {
  position: relative;
}
.tab-active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: hsl(var(--foreground));
  border-radius: 1px 1px 0 0;
}
```

### Transition Animation

Tab content switch uses CSS `display` toggle (not opacity, not mount/unmount):

```tsx
{/* Chat — ALWAYS mounted, hidden when Graph active */}
<div className={cn("flex-1 overflow-hidden", activeTab !== 'chat' && "hidden")}>
  <ChatView ... />
</div>

{/* Graph — lazy-loaded, mounted on first activation */}
{hasActivatedGraph && (
  <div className={cn("flex-1 overflow-hidden", activeTab !== 'knowledge-graph' && "hidden")}>
    <Suspense fallback={<GraphLoadingSkeleton />}>
      <IssueKnowledgeGraphFull ... />
    </Suspense>
  </div>
)}
```

- `hasActivatedGraph` state in `IssueDetailPage` — set to `true` on first Graph tab click
- `display: none` (via `hidden` class) preserves all React state including Chat messages, pending approvals, streaming responses

---

## 8. Interaction Flow Diagrams

### Flow 1: "I want to see what's related to this issue"

```
User opens issue detail page
         │
         ▼
Issue detail page loads
Knowledge Graph section (collapsed by default)
         │
         ▼ User clicks "▸ Knowledge Graph" section header
         │
Section expands
Mini-graph loads (200px, TanStack Query fetches graph data)
Shows 12 nodes with colored circles and connecting lines
         │
         ▼ User hovers over a node
         │
Tooltip appears: "PS-38 · Issue · Design auth flow"
         │
         ▼ User clicks "Expand full view →" button
         │
Right panel switches from Chat → Knowledge Graph tab
(Chat hidden, not unmounted)
IssueKnowledgeGraphFull loads (React.lazy, one-time cost)
Graph renders with full node labels, icons, zoom controls
         │
         ▼ User double-clicks on a "Decision" node
         │
API call: GET /nodes/{id}/neighbors?depth=1
New neighbor nodes appear with settle animation
         │
         ▼ User clicks on a "PS-38" (Issue) node
         │
Node selection: connected edges highlighted, others dimmed
Detail panel slides up from bottom:
  "PS-38: Design auth flow · Done · High Priority"
  [Open Issue →] [Expand neighborhood]
         │
         ▼ User clicks "Open Issue →"
         │
Navigate to: /workspace/issues/PS-38
```

### Flow 2: "I want to understand implementation scope before coding"

```
User opens issue detail page (PS-42: Implement auth flow)
         │
         ▼ User clicks "▸ GitHub & Implementation" section header
         │
Section expands showing:
  Area 1: PRs, branches, commits
  ──── separator ────
  Area 2: Implementation Plan
    Branch: feat/PS-42-auth-flow
    Tasks: 4 items (1 checked, 3 unchecked)
    CLI: pilot implement PS-42
    Affected Nodes: auth_module, rls_policies, "Chose Supabase Auth", auth-design.md
         │
         ▼ User clicks "● auth_module (code_ref)" in Affected Nodes
         │
Right panel switches to Knowledge Graph tab
IssueKnowledgeGraphFull renders with auth_module node
  highlighted (blue pulse animation, 3 cycles)
Detail panel opens showing auth_module details
         │
         ▼ User double-clicks auth_module node
         │
Neighboring nodes expand:
  - The issue PS-42 (connected via "references")
  - A "Chose Supabase Auth" decision node (connected via "decided_in")
         │
         ▼ User clicks the Decision node
         │
Detail panel: "Chose Supabase Auth over custom JWT"
  [Expand neighborhood] → shows the 3 conversations that led to this decision
```

### Flow 3: "I want to understand what led to a decision"

```
User is in Full Graph view (Knowledge Graph tab active)
         │
         ▼ User sees a "Decision" node (amber diamond): "Chose adjacency tables"
User clicks it
         │
Detail panel slides up:
  "Chose adjacency tables over Apache AGE"
  · Decision · Created 2026-02-15
  · Related via: decided_in (to PS-67)
         │
         ▼ User clicks "Expand neighborhood"
         │
API call: GET /nodes/{id}/neighbors?depth=1
New nodes appear:
  - PS-67 (Issue: "Design knowledge graph schema")  — decided_in edge
  - ConversationSummary node (summarizes the decision discussion) — summarizes edge
  - LearnedPattern node ("AGE not supported on Supabase") — learned_from edge
         │
         ▼ User clicks ConversationSummary node
         │
Detail panel shows conversation excerpt
(no "Open →" link for AI artifact nodes — information is self-contained)
```

---

## 9. Accessibility Requirements

### Keyboard Navigation

| Action | Keyboard Shortcut |
|--------|------------------|
| Switch to Knowledge Graph tab | Tab to tab button, Enter |
| Switch back to Chat tab | Tab to tab button, Enter |
| Navigate between nodes in graph | Tab (cycles through all rendered nodes) |
| Select focused node | Enter |
| Expand node neighborhood | Double-tap Enter (on selected node) |
| Deselect / close detail panel | Escape |
| Dismiss tooltip | Escape or Tab away |
| Copy CLI command | Tab to copy button, Enter |

### ARIA Roles

| Component | ARIA Implementation |
|-----------|-------------------|
| Tab bar | `role="tablist"`, each tab `role="tab"` with `aria-selected` |
| Graph canvas | `role="application"` with `aria-label="Knowledge graph with {n} nodes and {m} edges centered on {issueLabel}"` |
| Each graph node | `role="button"` with `aria-label="{nodeType}: {label}"` and `aria-pressed` for selected state |
| Detail panel | `role="region"` with `aria-label="Node details"`, `aria-live="polite"` |
| Mini-graph | `role="img"` with `aria-label="Knowledge graph preview — {n} nodes"` |
| Affected nodes list | `role="list"`, each item `role="listitem"` + `role="button"` for clickable rows |

### Screen Reader Announcements

- On tab switch: "Knowledge Graph panel active" / "Chat panel active"
- On node selection: "Selected: {nodeType} — {label}. {n} connections."
- On node expansion: "{m} new nodes added to graph"
- On graph load: "Knowledge graph loaded with {n} nodes and {m} edges"
- On empty state: "No knowledge graph data yet. Use AI chat to build connections."

### WCAG 2.1 AA Compliance

- All interactive elements meet 4.5:1 contrast ratio (text) and 3:1 (UI components) against backgrounds
- Focus rings: `ring-2 ring-ring ring-offset-1` — visible in both light and dark mode
- Color is never the only way to convey information — node types also use shape and 2-letter abbreviation
- Touch targets: minimum 44×44px for all interactive elements in the graph
- Graph nodes in full view: minimum 40×28px (well above touch target minimum)

### Reduced Motion

When `prefers-reduced-motion: reduce`:
- Force-directed layout animation skipped — nodes rendered at final computed positions immediately
- Highlight pulse replaced with a single non-animated ring
- Tab transition is instant (0ms)
- Node hover uses opacity change only (no scale transform)
- Detail panel appears instantly

---

## 10. Loading, Error, and Empty States

### Mini-Graph

#### Loading State (Skeleton)

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│   ●━━  ──  ●━━          ← 3 pulsing circles              │
│                ╲        (animate-pulse CSS class)        │
│                ●━━                                       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

- 3 circles: `w-5 h-5 rounded-full bg-muted animate-pulse`
- 2 connecting lines: `h-px w-8 bg-muted animate-pulse`
- Duration: shown while `useIssueKnowledgeGraph` is in `isLoading` state

#### Error State

```
┌──────────────────────────────────────────────────────────┐
│  ⚠  Failed to load graph.  [Retry]                      │
└──────────────────────────────────────────────────────────┘
```

- `AlertTriangle` icon (Lucide), `text-muted-foreground text-xs`
- `[Retry]` button: `Button` ghost xs, calls `refetch()`

#### Empty State

See Section 4 ("No graph data yet.")

---

### Full Graph

#### Loading State (Skeleton)

Full panel skeleton with animated placeholder nodes:

```
┌──────────────────────────────────────────────────────┐
│  [━━━━━━━]  [━━━━━━] [━━] [━━━] [━━━] [━━]  [━━━]  │  ← Toolbar skeleton
├──────────────────────────────────────────────────────┤
│                                                      │
│   ┌─────┐     ┌─────┐      ┌─────┐                  │
│   │ ━━━ │     │ ━━━ │      │ ━━━ │  ← Node skeletons│
│   └─────┘     └─────┘      └─────┘  (animate-pulse) │
│        ╲           │       ╱                         │
│         ╲──────────┼──────╱    ← Edge skeletons      │
│                    │                                 │
│               ┌─────┐                               │
│               │ ━━━ │                               │
│               └─────┘                               │
│                                                      │
└──────────────────────────────────────────────────────┘
```

- 5-7 rectangular `Skeleton` components in approximate graph layout positions
- Lines connecting them via CSS (absolute positioned divs)

#### Error State

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│         ⚠  Failed to load knowledge graph            │
│            {error.message if ApiError}               │
│                                                      │
│                       [Retry]                        │
│                                                      │
└──────────────────────────────────────────────────────┘
```

- Centered vertically in the canvas area
- `[Retry]` button: `Button` default variant

#### Empty State

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│         ◇ ── ○ ── □                                  │
│         (gentle opacity pulse animation)             │
│                                                      │
│      No knowledge graph yet                          │
│      The graph builds as you use AI features,        │
│      link issues, and make decisions.                │
│                                                      │
│              [Open AI Chat →]                        │
│                                                      │
└──────────────────────────────────────────────────────┘
```

- SVG illustration: 3 different shapes (diamond, circle, square) with connecting lines
- Animation: `opacity: 0.6 → 1.0 → 0.6`, 2s loop (disabled with `prefers-reduced-motion`)
- `[Open AI Chat →]` button: `Button` default variant, triggers tab switch to Chat

---

### Implementation Plan (Area 2 of GitHub Section)

#### Loading State

```
┌──────────────────────────────────────────────────────┐
│  Implementation Plan                                 │
│                                                      │
│  Branch: ━━━━━━━━━━━━━━━━                           │
│                                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━                            │
│  ━━━━━━━━━━━━━━━━                                   │
│  ━━━━━━━━━━━━━━━━━━━━━━━━                           │
└──────────────────────────────────────────────────────┘
```

- 3 `Skeleton` rows representing task items

#### Error State

```
┌──────────────────────────────────────────────────────┐
│  Implementation Plan                                 │
│                                                      │
│  ⚠  {error message from ApiError.fromAxiosError}    │
│     403 → "Access denied" | 422 → "Invalid request" │
│     other → "Failed to load implementation plan"    │
│                                                      │
└──────────────────────────────────────────────────────┘
```

#### Empty State (No AI Context Yet)

```
┌──────────────────────────────────────────────────────┐
│  Implementation Plan                                 │
│                                                      │
│  No plan generated yet.                              │
│                                                      │
│            [Generate Plan]                           │
└──────────────────────────────────────────────────────┘
```

- `[Generate Plan]` button triggers existing AI context generation

---

### GitHub Activity (Area 1) — No Change from Current

Loading state, error state, and empty state for the GitHub activity area remain unchanged from the current `GitHubSection` implementation.

---

## Appendix: Component File Index

| Component | File Path | New / Modified |
|-----------|-----------|---------------|
| `GitHubImplementationSection` | `frontend/src/features/issues/components/github-implementation-section.tsx` | New (replaces `github-section.tsx`) |
| `IssueKnowledgeGraphMini` | `frontend/src/features/issues/components/issue-knowledge-graph-mini.tsx` | New |
| `IssueKnowledgeGraphFull` | `frontend/src/features/issues/components/issue-knowledge-graph-full.tsx` | New |
| `IssueNoteLayout` | `frontend/src/features/issues/components/issue-note-layout.tsx` | Modified (tab system) |
| `IssueEditorContent` | `frontend/src/features/issues/components/issue-editor-content.tsx` | Modified (swap GitHubSection → GitHubImplementationSection, add mini-graph section) |
| `IssueDetailPage` | `frontend/src/app/(workspace)/[workspaceSlug]/issues/[issueId]/page.tsx` | Modified (rightPanelTab state, connect handlers) |
| `useIssueKnowledgeGraph` | `frontend/src/features/issues/hooks/use-issue-knowledge-graph.ts` | New |
| `useImplementationPlan` | `frontend/src/features/issues/hooks/use-implementation-plan.ts` | New |
| `knowledgeGraphApi` | `frontend/src/services/api/knowledge-graph.ts` | New |
| Design tokens | `frontend/src/styles/globals.css` | Modified (add `--graph-*` tokens) |

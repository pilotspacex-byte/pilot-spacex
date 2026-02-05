# Research Decisions — 008: Thinking & Tool Call UX

## RD-001: Elapsed Time Implementation

**Question**: How to display a live elapsed time counter on thinking blocks and tool cards?

| Option | Pros | Cons |
|--------|------|------|
| A) `setInterval(1000)` | Simple, familiar | Drift over time, runs in background tabs (wasted CPU), cleanup complexity with React strict mode |
| B) `requestAnimationFrame` with 1Hz throttle | Pauses when tab hidden, precise, no drift, natural cleanup | Slightly more code than setInterval |
| C) MobX computed from store timestamp | Reactive, no hook needed | Forces store update every second (unnecessary re-renders across all observers) |

**Decision**: **B) requestAnimationFrame with 1Hz throttle**

**Rationale**: FR-003 requires elapsed time updating every second. rAF pauses when the tab is hidden (saves battery/CPU), avoids setInterval drift, and cleanup is a single `cancelAnimationFrame`. The hook returns a formatted string, so components re-render only when the display value changes.

---

## RD-002: Tool Name Mapping Location

**Question**: Where should the mapping from raw tool function names to human-readable display names live?

| Option | Pros | Cons |
|--------|------|------|
| A) Backend sends display names in SSE events | Single source of truth, no frontend maintenance | Requires backend changes (out of scope), increases event payload |
| B) Frontend constant map | No backend changes, easy to maintain, immediate | Needs manual sync if tool names change |
| C) i18n locale file | Supports internationalization | Over-engineered for 6 tool names, adds i18n dependency |

**Decision**: **B) Frontend constant map**

**Rationale**: User clarification confirmed frontend-only scope. Only 6 MCP tools to map. Constant lives in `features/ai/ChatView/constants.ts` alongside existing skill/agent definitions. If tool names change, the map is a single-line edit.

---

## RD-003: Timeline Component Style

**Question**: What visualization style for the tool execution timeline?

| Option | Pros | Cons |
|--------|------|------|
| A) Horizontal Gantt chart | Shows parallelism clearly, familiar from devtools | Requires charting library (D3/recharts), horizontal space constrained in chat panel, complex |
| B) Vertical step list (pure Tailwind) | Fits chat flow, no new deps, simple, user-selected | Less precise about parallel timing |
| C) Third-party timeline library | Feature-rich | New dependency, bundle size, customization friction |

**Decision**: **B) Vertical step list**

**Rationale**: FR-013 needs a view for 3+ tool calls. User explicitly selected vertical step list in clarification. Fits the vertical chat flow naturally. Pure CSS/Tailwind implementation with no new dependencies. Parallel tools shown on same "level" with branching indicator.

---

## RD-004: Token Budget Ring Style

**Question**: What UI element for the token budget indicator?

| Option | Pros | Cons |
|--------|------|------|
| A) shadcn Progress bar | Already available, horizontal | Doesn't fit compact toolbar area, user wanted circular |
| B) SVG circle with stroke-dasharray | Precise, compact (24px), user-selected | Custom SVG code |
| C) CSS conic-gradient | Pure CSS, no SVG | Browser support quirks, harder to animate color transitions |

**Decision**: **B) SVG circle with stroke-dasharray**

**Rationale**: FR-014, user selected circular ring. SVG gives precise control over arc length via `stroke-dasharray`, supports smooth color transitions via CSS custom properties, and renders at 24px without pixelation.

---

## RD-005: Banner Positioning

**Question**: Where should the streaming state banner appear?

| Option | Pros | Cons |
|--------|------|------|
| A) Inline with messages (current approach) | Scrolls with content, visible in context | Invisible when user scrolls up, redundant with per-message indicators |
| B) Fixed above chat input | Always visible, acts as status bar | Takes 36px vertical space during streaming |
| C) Both inline and fixed | Maximum visibility | Redundant information, cluttered |

**Decision**: **B) Fixed above input**

**Rationale**: FR-007 requires a persistent indicator. User confirmed this in clarification. 36px height is minimal. Banner only appears during active streaming and disappears on completion.

---

## RD-006: Auto-Collapse Mechanism

**Question**: How to animate the thinking block collapse when thinking completes?

| Option | Pros | Cons |
|--------|------|------|
| A) CSS transition on height via shadcn Collapsible | Smooth animation, existing component | Collapsible already handles this |
| B) Conditional render (mount/unmount) | Simplest | No animation, jarring UX |
| C) max-height transition with overflow | Pure CSS | Requires known max-height, can be janky |

**Decision**: **A) CSS transition via shadcn Collapsible**

**Rationale**: FR-004 requires smooth auto-collapse. The existing `Collapsible` component from shadcn/ui already provides animated open/close with Radix primitives. The `ThinkingBlock` already uses button-based expand/collapse — switching to controlled `Collapsible` with `open` prop driven by `isStreaming` state gives us auto-collapse for free.

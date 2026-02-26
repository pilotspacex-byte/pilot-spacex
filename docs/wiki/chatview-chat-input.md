# ChatView: ChatInput System

> **Location**: `frontend/src/features/ai/ChatView/ChatInput/`
> **Design Decision**: DD-086 (Centralized Agent Architecture)

## Overview

The ChatInput system is the **interaction control center** of the AI ChatView. It is a resizable textarea augmented with three contextual command menus, real-time context display, working state indicators, and token budget tracking. It is _not_ a simple text box — it is an intent-detection engine that detects slash commands, agent mentions, and session resume triggers and routes each to the appropriate subsystem.

---

## Architecture

```
ChatInput (orchestrator)
├── Textarea (auto-resize, trigger detection)
├── ContextIndicator        ← shows attached note/issue/project context
├── WorkingIndicator        ← spinner + rotating idioms during streaming
├── SkillMenu               ← triggered by \ ; slash-command autocomplete
├── AgentMenu               ← triggered by @ ; agent selector
├── SessionResumeMenu       ← triggered by \resume ; session history picker
└── Token budget ring       ← live token consumption display
```

**Hooks**:
- `useSkills()` — fetches available skills from backend API with 30-min cache + hardcoded fallback
- `useIntentRehydration()` — restores `detected`/`executing` intents from backend on mount (post-refresh recovery)

---

## Components

### `ChatInput.tsx`

**Responsibility**: Orchestrates the entire input subsystem — textarea state, trigger detection, menu coordination, keyboard handling, and auto-resize.

**Props**:
```typescript
interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isStreaming?: boolean;
  isDisabled?: boolean;
  autoFocus?: boolean;
  noteContext?: NoteContext | null;
  issueContext?: IssueContext | null;
  projectContext?: ProjectContext | null;
  onClearNoteContext?: () => void;
  onClearIssueContext?: () => void;
  onClearProjectContext?: () => void;
  tokenBudgetPercent?: number;
  tokensUsed?: number;
  tokenBudget?: number;
  sessions?: SessionSummary[];
  sessionsLoading?: boolean;
  onSelectSession?: (sessionId: string) => void;
  onSearchSessions?: (query: string) => void;
  onNewSession?: () => void;
}
```

**Trigger Detection** (via `useEffect` on `value`):

| Trigger Pattern | Menu Opened | Replacement |
|----------------|-------------|-------------|
| `\` at word boundary | `SkillMenu` | `\skillname ` |
| `@` at word boundary | `AgentMenu` | `@agentname ` |
| `\resume` regex match | `SessionResumeMenu` | trigger removed |
| `\new` selected | No menu | triggers `onNewSession()` |

**Keyboard map**:

| Key | Condition | Action |
|-----|-----------|--------|
| `Enter` | No menu open, not streaming, value not empty | Submit |
| `Shift+Enter` | Any | Newline |
| `Escape` (in SkillMenu) | Menu open | Close + remove `\` |
| `Escape` (in AgentMenu) | Menu open | Close + remove `@` |
| `Backspace` (in SkillMenu search, empty) | Menu open | Close + remove `\` |
| Arrow Up/Down (in any menu) | Menu open | Navigate cmdk list |
| `Enter` (in any menu) | Item highlighted | Select item |

**Auto-resize**: Clamps between `40px` (min) and `160px` (≈4 lines) using `scrollHeight` measurement on every value change.

**Popover width sync**: A `ResizeObserver` on the container measures width and passes it to all three menus so popovers stay pixel-aligned as the viewport resizes.

---

### `SkillMenu.tsx`

**Responsibility**: Slash-command autocomplete for invoking AI skills, grouped by category, with keyboard navigation.

**Skill sources** (merged in order):
1. `SESSION_SKILLS` — always present: `\resume`, `\new`
2. Backend API skills (via `useSkills()`)
3. `FALLBACK_SKILLS` — hardcoded; used when API fails

**Categories**: Session → Writing → Notes → Issues → Code → Documentation → Planning

**Why categories?** The skill list is long enough that flat display is overwhelming. Categories let users scan by intent rather than reading every item.

**Key behaviors**:
- Filters by search input in real-time
- `Escape` or `Backspace` on empty search closes menu **and** calls `onCancel` to remove the `\` from the textarea
- `\resume` special-cased: clears `\` and opens `SessionResumeMenu` instead of inserting text
- `\new` special-cased: clears `\` and calls `onNewSession()` immediately

---

### `AgentMenu.tsx`

**Responsibility**: Agent mention selector (`@agentname`) for routing conversations to specialized subagents.

**Static agents** (hardcoded in `constants.ts`):

| Agent name | Subagent | Capabilities |
|-----------|---------|-------------|
| `@pr-review` | PRReviewAgent | Code review, security audit, architecture analysis |
| `@ai-context` | AIContextAgent | Multi-turn context aggregation for issues |
| `@doc-generator` | DocGeneratorAgent | Technical documentation from code |

**Why hardcoded?** Agents are core architectural pillars (DD-086), not dynamically added like skills. There is no backend endpoint to discover agents; they are static routing targets.

**Selection**: Replaces trailing `@` with `@agentname ` (note trailing space), giving users room to type context after the mention.

---

### `ContextIndicator.tsx`

**Responsibility**: Compact badge display showing what context is attached to the current conversation, with X dismiss buttons.

**Renders when**: At least one of `noteContext`, `issueContext`, or `projectContext` is non-null.

**Badge content**:
- **Note**: `FileText` icon + note title (truncated to 200px) + block count if a selection exists. Tooltip explains whether whole note or specific blocks are in context.
- **Issue**: `ListTodo` icon + issue title.
- **Project**: `FolderOpen` icon + project name.

**Value**: Transparency — user sees exactly what data the AI can read. Dismiss buttons prevent accidental context leakage.

---

### `SessionResumeMenu.tsx`

**Responsibility**: Session history picker that lets users resume a prior conversation.

**Triggered by**: `\resume` command in the textarea.

**Date grouping**:
- **Today** — same calendar day
- **Yesterday** — prior calendar day
- **Day name** — e.g., "Monday", "Friday" (last 7 days)
- **Date** — e.g., "February 15", "March 3, 2025" (older)

**Per-session display**:
- Title (first user message or "Untitled conversation")
- Up to 3 unique context badges (notes + issues seen across the session's history)
- Turn count ("5 turns")
- Relative time ("2h ago", "3d ago", "Feb 15")

**Why date grouping?** Users recall sessions temporally ("the one from yesterday"). Date buckets are faster to scan than a flat reverse-chronological list.

**Selection flow**: Removes `\resume` from textarea → calls `onSelectSession(sessionId)` → parent (ChatView) fetches full session data and loads message history.

---

### `WorkingIndicator.tsx`

**Responsibility**: Visual feedback while the AI is streaming a response.

**Behavior**: Visible when `isStreaming={true}`. Unmounts completely when idle (returns `null`).

**Idiom rotation**: 8 phrases cycling every 3 seconds ("Thinking deeply…", "Analyzing context…", "Connecting the dots…", etc.)

**Why rotating messages?** A static spinner reads as "frozen" after a few seconds. Rotation signals liveness without being alarming.

**Accessibility**: `role="status"` + `aria-live="polite"` announces changes to screen readers. `motion-reduce:animate-none` respects `prefers-reduced-motion`.

---

## Hooks

### `useSkills.ts`

**Purpose**: Fetch available skills from the backend API with caching and graceful fallback.

**Cache policy**:
- `staleTime`: 30 minutes — skills rarely change mid-session
- `gcTime`: 1 hour — memory-efficient
- `retry`: 1 — fail-fast on backend outage

**Merge order**: `SESSION_SKILLS` + (API skills OR `FALLBACK_SKILLS`)

**Why fallback?** Skills must always be available even if the backend is unreachable. Users can still invoke hardcoded skills (`\extract-issues`, `\improve-writing`, etc.) from the fallback list.

---

### `useIntentRehydration.ts`

**Purpose**: On ChatView mount (or workspace switch), restore `detected` and `executing` intents from the backend into MobX store without duplicating live state.

**Problem solved**: User refreshes page mid-conversation with pending approvals. Without rehydration, the approval UI would flash empty until the next SSE event. With rehydration, pending `IntentCard`s and `SkillProgressCard`s render immediately.

**Guards**:
- `hydrated.current` tracks which workspace was last hydrated → prevents redundant API calls on re-renders
- `if (!store.intents.has(intent.id))` → never overwrites live state with stale API data
- Both `detected` and `executing` fetches are independently try/caught → non-critical; failure doesn't break UI

**MobX integration**: Updates run inside `runInAction()` because async fetches happen outside MobX reactions.

---

## Data Flow

```
ChatView (parent)
  ├─ isStreaming ──────────────────> ChatInput
  │                                  ├─> WorkingIndicator (visible)
  │                                  └─> Textarea (disabled)
  │
  ├─ value / onChange ─────────────> ChatInput ↔ Textarea
  │
  ├─ noteContext/issueContext ──────> ContextIndicator (badges)
  │   onClear* callbacks ──────────> ContextIndicator (X buttons)
  │
  ├─ sessions / onSelectSession ───> SessionResumeMenu
  │
  ├─ tokenBudget* ─────────────────> Token budget ring
  │
  └─ useIntentRehydration(store)
      └─> On mount: fetch intents → store.intents (MobX)
```

---

## Implicit Features

| Feature | How | Where |
|---------|-----|-------|
| Textarea auto-resize | `scrollHeight` clamped to 160px | `ChatInput.tsx` |
| Popover width sync | `ResizeObserver` on container | `ChatInput.tsx` |
| Auto-focus on mount | `autoFocus` prop → `textareaRef.focus()` | `ChatInput.tsx` |
| Trigger char cleanup on cancel | `onCancel` prop → parent removes `\` or `@` | `SkillMenu`, `AgentMenu` |
| 3-second idiom rotation | `setInterval` in `WorkingIndicator` | `WorkingIndicator.tsx` |
| Session date bucketing | Computed from `updatedAt` diff | `SessionResumeMenu.tsx` |
| Context badge deduplication | `Set<string>` per note/issue ID | `SessionResumeMenu.tsx` |
| Intent hydration (post-refresh) | Single-run on mount per workspace | `useIntentRehydration.ts` |
| Skill fallback on API failure | `mergeSkills()` uses hardcoded set | `useSkills.ts` |
| Skills always include `\resume`/`\new` | `SESSION_SKILLS` merged first | `constants.ts` |
| `motion-reduce` spinner | Tailwind `motion-reduce:animate-none` | `WorkingIndicator.tsx` |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Trigger detection via `useEffect` on `value` | Declarative; easy to add new triggers without branching the main handler |
| Controlled menus (open/onOpenChange in ChatInput) | Single source of truth; ensures at most one menu open at a time |
| Command-replacement (not append) | Clean UX; `\extract-issues ` not `\\extract-issues` |
| Skills dynamic (API) + SESSION_SKILLS static | UI-only commands (`\resume`, `\new`) don't need a backend endpoint |
| Agents hardcoded | Agents are architectural constants (DD-086), not dynamically configurable |
| Intent rehydration non-critical | Improves UX on refresh but must not block rendering |
| `useRef` for hydration guard | Avoids double-fetch without adding `workspaceId` to dependency arrays |

---

## Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `ChatInput/ChatInput.tsx` | ~327 | Main orchestrator |
| `ChatInput/AgentMenu.tsx` | ~110 | Agent mention picker |
| `ChatInput/SkillMenu.tsx` | ~184 | Slash-command autocomplete |
| `ChatInput/ContextIndicator.tsx` | ~123 | Active context badges |
| `ChatInput/SessionResumeMenu.tsx` | ~275 | Session history picker |
| `ChatInput/WorkingIndicator.tsx` | ~58 | Streaming feedback |
| `hooks/useSkills.ts` | ~59 | Skill fetch + cache + fallback |
| `hooks/useIntentRehydration.ts` | ~72 | Post-refresh intent restore |
| `constants.ts` | ~244 | Static skill/agent/category/tool definitions |
| `types.ts` | ~152 | Canonical ChatView type definitions |

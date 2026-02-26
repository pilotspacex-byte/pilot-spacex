# Pilot Space Editor: Issue Detail TipTap Editor + AI

> **Location**: `frontend/src/features/issues/`, `frontend/src/app/(workspace)/[workspaceSlug]/issues/[issueId]/page.tsx`
> **Design Decisions**: DD-003 (Human-in-the-Loop), DD-013 (Note-First), DD-086 (Centralized Agent)

## Overview

The Issue Detail page implements the **Note-First issue editing paradigm** (DD-013): issues have a full TipTap rich-text editor as their primary surface, with inline property management (`PropertyBlockNode`) at the top. The `PilotSpaceAgent` is always present as a chat panel on the right. The entire system works around a strict React 19 + MobX + TipTap constraint that mandates a context bridge pattern.

---

## Architecture: Component Hierarchy

```
IssueDetailPage (observer)
  │  — TanStack Query: issue, members, labels, cycles
  │  — Handlers: onUpdate (PATCH), onUpdateState (PUT /state)
  │  — AI initialization: setWorkspaceId + setIssueContext
  │
  └── IssueNoteContext.Provider
        (value: issue, members, labels, cycles, onUpdate, onUpdateState, disabled)
        │
        └── IssueNoteLayout (62% editor | 38% chat)
              │
              ├── IssueEditorContent (plain component — NOT observer())
              │     └── useEditor({ extensions: createIssueNoteExtensions() })
              │           ├── PropertyBlockNode ← position 0, always present
              │           │     └── ReactNodeViewRenderer(PropertyBlockView)
              │           │           └── PropertyBlockView (observer)
              │           │                 ├── reads: useIssueNoteContext()
              │           │                 ├── PropertyBlockExpanded
              │           │                 │     └── PropertyChip[] (state, priority, assignee, ...)
              │           │                 └── PropertyBlockCollapsed
              │           │                       └── PropertyChip[] (condensed)
              │           │
              │           └── [all note canvas extensions: GhostText, AnnotationMark,
              │                SlashCommand, InlineIssue, Markdown, ...]
              │
              └── ChatView (lazy Suspense, 38%)
                    ├── IssueChatEmptyState (4 AI command cards)
                    ├── MessageList (SSE streaming)
                    └── InputBar + SuggestedPrompts
```

---

## The React 19 + MobX + TipTap Constraint

### The Problem

React 19 enforces strict `flushSync` nesting rules. **Two things must never happen simultaneously**:

1. MobX `observer()` calling `useSyncExternalStore` → triggers `flushSync()`
2. TipTap's `ReactNodeViewRenderer` inside a ProseMirror transaction (during React render phase)

If `IssueEditorContent` were `observer()`, this sequence would cause the crash:

```
User types → TipTap editor.on('update') fires
    → TanStack mutation (optimistic update in cache)
    → MobX store updated
    → observer() triggers useSyncExternalStore
    → flushSync() called
    → Meanwhile: ReactNodeViewRenderer inside ProseMirror transaction
    → React 19: "flushSync was called from inside a lifecycle method" 💥
```

### The Solution: Context Bridge Pattern

```typescript
// IssueDetailPage (observer) — MobX reactivity at the top
const IssueDetailPage = observer(function IssueDetailPage() {
  const { issue, members, labels, cycles } = ...; // MobX/TanStack data
  return (
    <IssueNoteContext.Provider value={{ issue, members, ..., onUpdate, onUpdateState }}>
      <IssueEditorContent issue={issue} ... />  {/* NO observer() */}
    </IssueNoteContext.Provider>
  );
});

// IssueEditorContent — plain component (critical constraint)
export function IssueEditorContent({ issue, ... }) {
  // useEditor creates ReactNodeViewRenderer for PropertyBlockNode
  // Must NOT be observer() — no useSyncExternalStore here
}

// PropertyBlockView — observer() is safe here
// It's a CHILD of the ReactNodeViewRenderer transaction, not the parent
const PropertyBlockView = observer(function PropertyBlockView() {
  const { issue } = useIssueNoteContext(); // reads from context
  // MobX reactive reads here, isolated from editor's transaction
});
```

**Rule**: Never wrap with `observer()` any component that contains `useEditor()` with a `ReactNodeViewRenderer` extension, if that component tree is under another MobX observable.

---

## `PropertyBlockNode` — Inline Property Editor

### Extension (`property-block-extension.ts`)

A TipTap `Node` that renders at position 0 of every issue document. It shows the issue's properties (state, priority, assignee, cycle, labels, dates, effort) either expanded (full grid) or collapsed (single chip row).

**Node configuration**:
```typescript
PropertyBlockNode.configure({ issueId })
```

**HTML serialization**: `<div data-property-block></div>` — this div is stripped before saving to DB.

**Two guard plugins** (ProseMirror level):

#### Guard 1: `filterTransaction` — Prevent Deletion

```typescript
filterTransaction(tr, state) {
  if (!tr.docChanged) return true;

  const hadBlock = hasPropertyBlock(state.doc);
  const hasBlock = hasPropertyBlock(tr.doc);

  if (hadBlock && !hasBlock) return false; // Reject: would remove PropertyBlock
  return true;
}
```

Runs on every document transaction. If the PropertyBlock would disappear, the transaction is silently rejected. User cannot delete the property block by any means (Backspace, Ctrl+A+Delete, etc.).

#### Guard 2: `appendTransaction` — Safety Net

```typescript
appendTransaction(_trs, _oldState, newState) {
  if (!hasPropertyBlock(newState.doc)) {
    const tr = newState.tr.insert(0, nodeType.create());
    tr.setMeta('addToHistory', false); // Don't pollute undo history
    return tr;
  }
  return null;
}
```

Runs after all transactions. If somehow the PropertyBlock is missing, it is re-inserted at position 0. `addToHistory: false` ensures re-insertion doesn't create an undo step.

---

## Auto-Save: 2-Second Debounce

**Mechanism**: Every `editor.on('update')` event resets a 2000ms timer. When the timer fires, content is saved to `PATCH /api/v1/issues/{id}`.

**Three rules enforced before each save**:

1. **Strip PropertyBlock div**:
   ```typescript
   const cleanHtml = html.replace(/<div[^>]*data-property-block[^>]*><\/div>/g, '').trim();
   ```
   The `<div data-property-block></div>` is UI-only markup. It must not be persisted.

2. **Skip unchanged saves**:
   ```typescript
   if (cleanHtml === lastSavedHtmlRef.current) return;
   lastSavedHtmlRef.current = cleanHtml;
   ```
   Prevents duplicate API calls when user moves cursor without typing.

3. **Save both HTML and markdown**:
   ```typescript
   await onUpdate({
     description: editor.storage.markdown?.getMarkdown?.() ?? editor.getText(),
     descriptionHtml: cleanHtml,
   });
   ```
   Both are saved for compatibility with issue list views (use text) and detail editor (uses HTML).

**Cmd+S force save** (DOM event):
```typescript
// Keyboard handler dispatches:
document.dispatchEvent(new CustomEvent('issue-force-save'));

// IssueEditorContent listens:
document.addEventListener('issue-force-save', () => {
  clearDebounce();
  void saveDescription(editor.getHTML(), editor.getText());
});
```

---

## AI Integration: All Touch Points

### 1. Context Initialization (on page mount)

```typescript
useEffect(() => {
  store.setWorkspaceId(workspaceId);
  store.setIssueContext({ issueId });
  return () => store.setIssueContext(null); // Cleanup on unmount
}, [workspaceId, issueId]);
```

After this, every PilotSpaceAgent message automatically includes the issue context. MCP tools like `issue.update_issue` target the correct issue without the user specifying it.

### 2. Chat Panel — 38% Right Side

**Empty state** (`IssueChatEmptyState`) — when no messages exist:

```
┌────────────────────────────────────────────────┐
│  ┌──────────────┐  ┌──────────────────────┐   │
│  │  Generate    │  │   Gather AI context  │   │
│  │ description  │  │                      │   │
│  └──────────────┘  └──────────────────────┘   │
│  ┌──────────────┐  ┌──────────────────────┐   │
│  │  QA this     │  │ Decompose into tasks  │   │
│  │   issue      │  │                      │   │
│  └──────────────┘  └──────────────────────┘   │
└────────────────────────────────────────────────┘
```

| Card | Prompt sent to PilotSpaceAgent |
|------|-------------------------------|
| Generate description | Generates structured description (Problem, Acceptance, Technical) |
| Gather AI context | Analyzes dependencies, related issues, implementation hints |
| QA this issue | Reviews completeness: title, description, criteria, assignee, priority |
| Decompose into tasks | Breaks into atomic sub-tasks with estimates |

**SuggestedPrompts** (below input bar): 4 preset AI prompts always visible at the bottom of chat. Different from empty state cards — these persist even when messages exist.

### 3. Description Empty State CTA

When the TipTap editor has no content:
```
┌────────────────────────────────────────────────┐
│  ✨ Generate with AI Chat                      │
│     Opens chat + sends generate prompt         │
└────────────────────────────────────────────────┘
```

Handler:
```typescript
const handleAiGenerateFromEditor = useCallback(() => {
  setIsChatOpen(true);
  if (!pilotSpaceStore.isStreaming) {
    pilotSpaceStore.sendMessage(generateDescriptionPrompt);
  }
}, [pilotSpaceStore]);
```

Guards against double-send if chat is already streaming.

### 4. AI-Generated Update Cycle

When PilotSpaceAgent modifies the issue via MCP tools:
```
Agent calls: issue.update_issue({ description: "..." })
    ↓
Backend updates DB
    ↓
Agent fires: window.dispatchEvent(
  new CustomEvent('pilot:issue-updated', { detail: { issueId } })
)
    ↓
IssueDetailPage listener: if (updatedId === issueId) { await refetch() }
    ↓
On success: setEditorKey(k => k + 1)  ← forces IssueEditorContent remount
    ↓
useEditor() re-initializes with fresh issue.descriptionHtml
    ↓
PropertyBlockView re-reads updated issue from context
```

The `editorKey` remount is intentional — it's the simplest way to fully reinitialize TipTap with new content without managing incremental content updates.

### 5. Task Progress Widget

After `Decompose into tasks` or `\decompose-tasks` skill:

```
┌────────────────────────────────────────────────┐
│ 🗂 Implementation Tasks                       │
│ [████████░░░░░░] 3 of 8 completed             │
│                               [View all →]    │
└────────────────────────────────────────────────┘
```

- `TaskProgressWidget` reads from `TaskStore` (MobX)
- Updates in real-time as tasks are completed (Supabase Realtime)
- "View all" opens task list panel

### 6. Approval Workflow (DD-003) in Issue Context

```typescript
const issueApprovals = useMemo(() => {
  return aiStore.pilotSpace.pendingApprovals?.filter(
    (r) => r.affectedEntities.some(e => e.type === 'issue' && e.id === issueId)
  );
}, [aiStore.pilotSpace.pendingApprovals, issueId]);

// Auto-route based on destructiveness
useEffect(() => {
  if (issueApprovals.length === 0) return;
  if (destructiveApproval) {
    setDestructiveModalOpen(true);
  } else {
    setIsChatOpen(true); // Show inline in chat
  }
}, [issueApprovals]);
```

| Action Type | UI | Auto-opens |
|-------------|-----|-----------|
| `update_issue` (fields) | InlineApprovalCard in chat | Chat panel |
| `create_sub_issue` | InlineApprovalCard in chat | Chat panel |
| `delete_issue` | DestructiveApprovalModal (blocking) | Modal overlay |
| `bulk_update` | DestructiveApprovalModal | Modal overlay |

---

## `onUpdate` vs `onUpdateState`: Two Mutation Paths

**`onUpdate(data: UpdateIssueData)`**

- **Endpoint**: `PATCH /api/v1/issues/{id}`
- **Used for**: priority, assignee, cycle, labels, dates, estimate, description
- **Hook**: `useUpdateIssue(workspaceId, issueId)`
- **Optimistic update**: TanStack Query `onMutate` updates cache immediately

**`onUpdateState(state: IssueState)`**

- **Endpoint**: `PUT /api/v1/issues/{id}/state` (dedicated state machine endpoint)
- **Accepts**: state name string (`'todo'`, `'in_progress'`, etc.), NOT UUID
- **Used for**: state transitions only (state machine logic, cycle constraints)
- **Ordering in PropertyBlockView**:

```typescript
// Start mutation FIRST (optimistic update in TanStack Query cache)
const pending = onUpdateState(state);
// THEN wrap with save status tracking
wrapState(() => pending).catch(() => {});
```

This ordering prevents a "save status blink" where the UI would briefly show the old state before the optimistic update arrives.

---

## Per-Field Save Status

Each property mutation has independent save status tracking:

```typescript
const { wrapMutation: wrapPriority } = useSaveStatus('priority');

const handlePriorityChange = (priority: IssuePriority) => {
  wrapPriority(() => onUpdate({ priority })).catch(() => {});
};
```

`useSaveStatus` tracks: `idle` → `saving` → `saved` → `idle` (auto-clear 2s), or `error`.

The `FieldSaveIndicator` component renders per-field:
- `saving`: spinning `Loader2` icon
- `saved`: `Check` icon (green)
- `error`: `AlertCircle` icon (red, persistent until next mutation)

---

## PropertyBlockView UI

### Expanded Mode (default)

```
State:       [● In Progress]
Priority:    [↑ High]
Assignee:    [A Avatar Name]
Cycle:       [Sprint 5 - Active]
Due Date:    [Jan 15, 2025]
Labels:      [bug] [frontend]
Effort:      [3 pts]
```

Each chip is a `<button>` that opens a Radix Popover with the appropriate selector (IssueStateSelect, AssigneeSelector, etc.).

### Collapsed Mode

```
[● In Progress] [↑ High] [A] [Jan 15] [+2 labels]
```

Single row of chips. Click any chip to expand the PropertyBlock to full view.

---

## Implicit Features

| Feature | Mechanism | File |
|---------|-----------|------|
| PropertyBlock re-insertion safety net | `appendTransaction` guard | `property-block-extension.ts` |
| Editor remount on AI update | `setEditorKey(k => k+1)` | `page.tsx` |
| Cleanup issue context on unmount | `setIssueContext(null)` in effect cleanup | `page.tsx` |
| Lazy ChatView load | `React.lazy()` + Suspense | `page.tsx` |
| Save dedup | `lastSavedHtmlRef` comparison | `issue-editor-content.tsx` |
| onUpdateState optimistic ordering | mutation before wrapMutation | `property-block-view.tsx` |
| Describe prompts insert H3 | `editor.commands.insertContent('<h3>...')` | `issue-description-empty-state.tsx` |
| AI generate guard (no double-send) | `pilotSpaceStore.isStreaming` check | `page.tsx` |
| Mobile: chat as slide-over | `NoteCanvasMobileLayout` responsive switch | `issue-note-layout.tsx` |
| Approval auto-route | Checks `actionType === 'delete'` or similar | `page.tsx` |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| `IssueEditorContent` not observer() | React 19 nested flushSync. MobX + TipTap ReactNodeViewRenderer cannot coexist in same component tree level. |
| Context bridge (IssueNoteContext) | PropertyBlockView needs live issue data. Passing via TipTap node attributes is limited and requires serialization. Context is direct. |
| Two PropertyBlock guards | Deletion guard (filterTransaction) is the primary. appendTransaction is the safety net for edge cases (plugin ordering bugs). |
| `addToHistory: false` on re-insert | Re-inserting PropertyBlock is a system action, not user action. It shouldn't be undoable. |
| 2s debounce auto-save | Matches Note Canvas standard (CLAUDE.md). Low enough for user confidence; high enough to batch rapid edits. |
| `pilot:issue-updated` custom event | Decouples PilotSpaceAgent from React rendering. Agent doesn't need React refs; it fires a DOM event and React handles the rest. |
| editorKey++ on AI update | Simplest correct implementation. Incremental TipTap content updates are complex (position tracking, marks, etc.). Full remount guarantees correctness. |
| Separate `PUT /state` endpoint | State transitions involve state machine logic, cycle constraints, event sourcing. Merging with PATCH would complicate both endpoints. |
| PATCH with `description` + `descriptionHtml` | `description` (markdown text) is used by issue list views and API consumers; `descriptionHtml` is used by the TipTap editor. Both needed. |

---

## Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `app/(workspace)/[workspaceSlug]/issues/[issueId]/page.tsx` | ~380 | Page: TQ hooks, context setup, AI init, approval routing |
| `features/issues/components/issue-editor-content.tsx` | ~250 | TipTap editor mount, auto-save, NOT observer() |
| `features/issues/editor/property-block-extension.ts` | ~150 | PropertyBlockNode + 2 guard plugins |
| `features/issues/editor/create-issue-note-extensions.ts` | ~80 | Extension factory (prepends PropertyBlockNode) |
| `features/issues/contexts/issue-note-context.ts` | ~60 | Context type + hook |
| `features/issues/components/property-block-view.tsx` | ~280 | Expanded property grid (observer) |
| `features/issues/components/property-block-collapsed.tsx` | ~150 | Collapsed chip row (observer) |
| `features/issues/components/property-chip.tsx` | ~120 | Individual chip + Radix Popover |
| `features/issues/components/issue-description-empty-state.tsx` | ~100 | Empty editor CTA + AI generate button |
| `features/issues/components/issue-chat-empty-state.tsx` | ~200 | 4 AI command cards + related notes/issues |
| `features/issues/components/task-progress-widget.tsx` | ~120 | AI task decomposition progress bar |
| `features/issues/components/suggested-prompts.tsx` | ~80 | 4 preset AI prompts in chat |
| `features/issues/components/issue-note-layout.tsx` | ~180 | 62/38 resizable layout, mobile slide-over |
| `features/issues/hooks/use-save-status.ts` | ~100 | Per-field save status (idle/saving/saved/error) |

# Pilot Space Editor: Issue Extraction & Slash Commands

> **Location**: `frontend/src/features/notes/editor/extensions/`, `frontend/src/features/notes/hooks/`
> **Design Decisions**: DD-003 (Human-in-the-Loop), DD-013 (Note-First), DD-088 (MCP Tools)

## Overview

Issue Extraction is the **core Note-First workflow** (DD-013): users write freely in the Note Canvas, then extract structured issues directly from the text. The `\extract-issues` slash command opens a streaming preview modal, the user selects candidates, approves the creation, and the source text gets highlighted with rainbow borders linked to the new `[PS-42]` inline badges. This is "Think first, structure later" made interactive.

Slash commands provide the broader AI action menu — 13+ commands spanning extraction, content improvement, diagram generation, and AI agent invocation.

---

## Architecture

```
User invokes via:
  a) Types `\` → SlashCommandExtension menu → select command
  b) Selects text → useSelectionAIActions toolbar → action button

Extraction flow:
SlashCommandExtension: handles input, shows menu, executes command
        ↓
slash-command-items.ts: defines all commands + handlers
        ↓
useIssueExtraction hook: manages extraction state (SSE + create)
        ↓
ExtractionPreviewModal: streams candidates, user selects
        ↓
POST /api/v1/issues/bulk-create (approved via DD-003)
        ↓
Backend: creates Issues + NoteIssueLink(EXTRACTED) records
        ↓
useIssueSyncListener: Supabase Realtime event received
        ↓
InlineIssueExtension: renders [PS-42] badge on source text
AIBlockProcessingExtension: shows rainbow border on extracted range

Content update flow (AI → TipTap):
useContentUpdates: consumes SSE content_update events
        ↓
contentUpdateHandlers: 10 operation type dispatcher
        ↓
TipTap editor commands applied
```

---

## Slash Command System

### `SlashCommandExtension.ts` — Command Menu

**Responsibility**: Intercepts `/` keypress, renders command menu, dispatches selected command.

**Trigger**: Any `/` at the start of a block or after whitespace.

**Architecture**: Uses TipTap's `Suggestion` utility (ProseMirror plugin) to:
1. Track `/` character insertion as "mention trigger"
2. Show floating menu component (`slash-command-menu.ts`)
3. Pass selected item to `onSelect` handler
4. Remove the trigger character on selection

**Filtering**: As user types after `/`, commands are filtered by prefix match on both `name` and `description`. Typing `\ext` shows `extract-issues` and `extend` but not `enhance`.

**Keyboard navigation**: Arrow Up/Down selects item; Enter executes; Escape closes (no command triggered).

---

### `slash-command-items.ts` — Command Registry

**Responsibility**: Defines all available slash commands with their metadata and handlers.

**Command structure**:
```typescript
interface SlashCommandItem {
  name: string;           // Command identifier (e.g., 'extract-issues')
  title: string;          // Display name (e.g., 'Extract Issues')
  description: string;    // Shown in menu and used for search
  icon: LucideIcon;
  category: 'ai' | 'insert' | 'format' | 'agent';
  execute: (editor: Editor, context: CommandContext) => void;
}
```

**AI commands** (relevant to this wiki):

| Command | Category | Handler |
|---------|----------|---------|
| `\extract-issues` | ai | Opens `ExtractionPreviewModal` |
| `\improve-writing` | ai | Triggers `improve-writing` skill via PilotSpaceAgent |
| `\summarize` | ai | Triggers `summarize` skill |
| `\generate-diagram` | ai | Triggers `generate-diagram` skill → Mermaid block insert |
| `\generate-pm-blocks` | ai | Triggers PM block generation (SprintBoard, RACI, etc.) |
| `@pr-review` | agent | Triggers `PRReviewSubagent` |
| `@doc-generator` | agent | Triggers `DocGeneratorSubagent` |
| `@ai-context` | agent | Triggers `AIContextAgent` |

**Insert commands** (non-AI, for reference):

| Command | Handler |
|---------|---------|
| `\heading1/2/3` | TipTap `toggleHeading({ level })` |
| `\code-block` | TipTap `toggleCodeBlock()` |
| `\divider` | TipTap `setHorizontalRule()` |
| `\checklist` | TipTap `toggleTaskList()` |

---

### `slash-command-menu.ts` — Menu UI

**Responsibility**: Renders the floating command menu attached to the cursor.

- Virtualizes items (shows top 8, scrollable)
- Groups by `category` with section headers
- Highlights matched characters in command name
- Uses `tippy.js` for positioning (follows cursor, never clips at viewport edge)

---

## Issue Extraction

### `useIssueExtraction.ts` — Extraction State Hook

**Responsibility**: Manages the full extraction lifecycle: SSE streaming, candidate state, creation, and deduplication.

**State**:
```typescript
interface ExtractionState {
  phase: 'idle' | 'streaming' | 'reviewing' | 'creating' | 'done' | 'error';
  candidates: IssueCandidate[];
  selectedIds: Set<string>;
  noteId: string | null;
  noteRange: { from: number; to: number } | null; // Source text range
}
```

**SSE streaming**:
```typescript
const stream = new EventSource(
  `/api/v1/ai/extract-issues?workspace_id=${workspaceId}&note_id=${noteId}&selected_text=${encodeURIComponent(selectedText)}`
);

stream.addEventListener('candidate', (e) => {
  const candidate: IssueCandidate = JSON.parse(e.data);
  // { id, title, description, type, confidence, sourceRange }
  runInAction(() => {
    extractionStore.addCandidate(candidate);
  });
});
```

Candidates stream as they are detected. The modal renders each candidate as it arrives — users start reading before extraction completes.

**Three extraction types** (from `IssueCandidate.type`):

| Type | Meaning | Default Selected |
|------|---------|-----------------|
| `explicit` | Text directly says "we need to..." or "TODO:" | Yes |
| `implicit` | Implied requirement from context | No (user must opt in) |
| `related` | Existing issues mentioned in the text | No |

**Deduplication guard** (500ms window):
```typescript
const recentCreations = useRef<Set<string>>(new Set());

const handleCreate = async (candidate: IssueCandidate) => {
  const key = candidate.title.toLowerCase().trim();
  if (recentCreations.current.has(key)) return; // Dedup
  recentCreations.current.add(key);
  setTimeout(() => recentCreations.current.delete(key), 500);
  await createIssue(candidate);
};
```

Prevents double-creation when user double-clicks "Create" or the SSE fires twice for the same candidate.

**Approval gate** (DD-003):
After user selects candidates and clicks "Create Issues", the hook calls:
```typescript
await approvalStore.requestApproval({
  actionType: 'bulk_create_issues',
  payload: { issues: selectedCandidates, noteId },
  tier: 'DEFAULT',
});
```
Approval is shown as an `InlineApprovalCard` in the modal itself. The actual `bulk_create_issues` MCP tool call only executes after user approves.

---

### `ExtractionPreviewModal.tsx` — Selection + Preview UI

**Responsibility**: Shows streaming extraction candidates with selection controls.

**Modal layout**:
```
┌─────────────────────────────────────────────────────┐
│  Extract Issues from Note                   [✕]    │
│                                                     │
│  Analyzing note... (streaming)                      │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │ ✓ Fix authentication middleware bug          │  │
│  │   Type: explicit  Confidence: 95%            │  │
│  │   "The auth middleware throws on expired..." │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │ □ Improve error logging for edge cases       │  │  ← implicit (opt-in)
│  │   Type: implicit  Confidence: 72%            │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  [Select All]  [Deselect All]      2 selected      │
│                             [Cancel]  [Create Issues] │
└─────────────────────────────────────────────────────┘
```

**Progressive rendering**: Each candidate renders as it streams. The modal height expands as more candidates arrive. User can interact (select/deselect) while streaming is still in progress.

**Candidate confidence display**: Color-coded confidence bars (green ≥80%, yellow 60-80%, red <60%). Low-confidence candidates have a `⚠` icon and are deselected by default.

---

## Post-Extraction: Inline Badges and Rainbow Borders

### `InlineIssueExtension.ts` + `InlineIssueComponent.tsx`

**Responsibility**: Renders `[PS-42]` inline badges within the note text that link to the created issue.

After `NoteIssueLink` records are created in the backend, `useIssueSyncListener.ts` receives a Supabase Realtime event:
```typescript
supabase
  .channel('note-issue-links')
  .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'note_issue_links' }, (payload) => {
    if (payload.new.note_id === noteId) {
      inlineIssueStore.addLink(payload.new);
    }
  })
  .subscribe();
```

`InlineIssueExtension` then renders a `NodeView` for each `issue_mention` node in the document — or inserts them at the `sourceRange` positions from the extraction result.

**Badge UI** (`InlineIssueComponent.tsx`):
```
[PS-42]
 ↑
 Clickable badge → opens issue detail page
 Color matches issue state (blue=in_progress, green=done, gray=backlog)
 Tooltip shows issue title on hover
```

**Rainbow border** (extraction highlight):
- Applied as a ProseMirror decoration (not a mark) around the source text range
- CSS: rotating gradient border animation (`@keyframes rainbow-rotate`)
- Duration: 3 seconds, then fades to a static blue border
- Indicates "this text was used to create these issues" — bidirectional link visible in editor

---

## AI Content Updates (MCP → TipTap)

### `useContentUpdates.ts` — SSE Event Consumer

**Responsibility**: Consumes `content_update` SSE events from PilotSpaceAgent and applies them to the TipTap editor.

```typescript
useEffect(() => {
  const unsubscribe = pilotSpaceStore.onContentUpdate((event: ContentUpdateEvent) => {
    contentUpdateQueue.current.push(event);
    scheduleFlush(); // Process next tick
  });
  return unsubscribe;
}, [pilotSpaceStore]);
```

Queue processing is deferred to prevent applying updates during TipTap transactions.

### `contentUpdateHandlers.ts` — Operation Dispatcher

**Responsibility**: Maps 10 operation types to TipTap editor commands.

```typescript
type ContentOperation =
  | { type: 'replace_block'; blockId: string; content: string }
  | { type: 'insert_after'; blockId: string; content: string }
  | { type: 'insert_before'; blockId: string; content: string }
  | { type: 'delete_block'; blockId: string }
  | { type: 'update_attributes'; blockId: string; attributes: Record<string, unknown> }
  | { type: 'replace_text'; from: number; to: number; text: string }
  | { type: 'insert_text'; position: number; text: string }
  | { type: 'delete_text'; from: number; to: number }
  | { type: 'set_heading'; blockId: string; level: 1 | 2 | 3 }
  | { type: 'wrap_in_list'; from: number; to: number; listType: 'bullet' | 'ordered' }
```

**Block ID resolution**: Before any operation, `blockId` (UUID) is resolved to a ProseMirror position using `BlockIdExtension.getPositionByBlockId(blockId)`. If the block no longer exists (deleted by user), the operation is silently skipped.

**Conflict detection**:
```typescript
// For destructive operations (replace_block, delete_block):
const currentContent = editor.getNodeAtPosition(pos)?.textContent;
const expectedContent = operation.expectedContent; // Sent by backend

if (currentContent !== expectedContent) {
  // Conflict: user edited the block after agent started modifying it
  conflictQueue.push({ operation, retryCount: 0 });
  scheduleConflictRetry(3000, 2); // Exponential backoff: 3s, 6s
}
```

Non-destructive operations (`insert_after`, `update_attributes`) bypass conflict detection.

---

## `AIBlockProcessingExtension.ts` — Visual Processing Indicator

**Responsibility**: Shows a visual indicator while AI is streaming content into a block.

**Indicator**: A spinning indicator appears on the left gutter of the block being processed. Implemented as a ProseMirror decoration that is added when `processingBlockId` is set, and removed when cleared.

**Processing state lifecycle**:
```typescript
// On content_update SSE start:
AIBlockProcessingExtension.setProcessing(blockId)
  → adds decoration: CSS spinner in block gutter

// On content_update SSE end:
AIBlockProcessingExtension.clearProcessing(blockId)
  → removes decoration
  → triggers 300ms "done" animation (green checkmark → fade)
```

---

## Selection-Based AI Actions

### `useSelectionAIActions.ts` — Selection Toolbar

**Responsibility**: When user selects text, shows a floating toolbar with AI action buttons.

**Floating toolbar actions** (appear on text selection):

| Action | Command | Skill Invoked |
|--------|---------|---------------|
| Improve Writing | `\improve-writing` with selection | `improve-writing` |
| Summarize | `\summarize` with selection | `summarize` |
| Extract Issue | `\extract-issues` for selection | `extract-issues` |
| Ask AI | Sends selected text to chat | PilotSpaceAgent |

**Selection context** (`useSelectionContext.ts`):
```typescript
interface SelectionContext {
  from: number;
  to: number;
  text: string;
  blockIds: string[];    // All block IDs within selection
  blockTypes: string[];  // Paragraph, heading, etc.
}
```

This context is passed to skill invocations so the AI knows exactly which content is being operated on.

---

## `NoteIssueLink` Bidirectional Relationship

| Link Type | Created When | UI in Editor |
|-----------|-------------|--------------|
| `EXTRACTED` | `\extract-issues` creates issues | Rainbow border + `[PS-42]` badge |
| `CREATED` | User manually creates issue from note | `[PS-42]` badge (no rainbow border) |
| `REFERENCED` | Agent calls `note.link_note_to_issue` | `[PS-42]` badge with paperclip icon |

The link type determines the visual treatment. `EXTRACTED` links have the richest highlighting because they represent the core Note-First workflow value.

---

## Implicit Features

| Feature | Mechanism | File |
|---------|-----------|------|
| Extraction deduplication (500ms) | `recentCreations` ref set | `useIssueExtraction.ts` |
| Progressive modal (streams as candidates arrive) | `EventSource` + `runInAction` | `useIssueExtraction.ts` |
| Realtime NoteIssueLink sync | Supabase Realtime on `note_issue_links` table | `useIssueSyncListener.ts` |
| Rainbow border animation | CSS `@keyframes rainbow-rotate`, 3s then fade | `InlineIssueExtension.ts` |
| Block ID resolution before operations | `BlockIdExtension.getPositionByBlockId()` | `contentUpdateHandlers.ts` |
| Conflict detection for destructive ops | `expectedContent` comparison + retry queue | `contentUpdateHandlers.ts` |
| Exponential backoff on conflict | 3s → 6s retry (max 2 attempts) | `contentUpdateHandlers.ts` |
| AI processing spinner in gutter | ProseMirror decoration on target block | `AIBlockProcessingExtension.ts` |
| `queueMicrotask()` for update deferral | Prevents flushSync during TipTap transaction | `useContentUpdates.ts` |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Rainbow border for EXTRACTED links | Permanent visual connection between source text and derived issues. Users can always trace where an issue came from. |
| Streaming extraction modal | User reads first candidates while others generate. Reduces perceived wait time. |
| `explicit` selected by default, `implicit` opt-in | Explicit items have high confidence. Implicit items require human judgment. Auto-selecting all would create noise. |
| Conflict detection for destructive MCP updates | Agent may be 5s behind user edits. Overwriting user's recent changes without checking destroys work. |
| `queueMicrotask()` before TipTap dispatch | Content updates arrive via SSE callbacks. Deferring with microtask ensures TipTap is not mid-transaction when update applies. |
| Block ID extension as universal resolver | Block positions shift when content changes. BlockId (UUID) is stable; extension maintains ID→position map. |

---

## Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `editor/extensions/SlashCommandExtension.ts` | ~200 | Command menu, trigger detection, menu dispatch |
| `editor/extensions/slash-command-items.ts` | ~350 | All command definitions, handlers, categories |
| `editor/extensions/slash-command-menu.ts` | ~150 | Floating menu UI, keyboard nav, tippy.js |
| `editor/extensions/AIBlockProcessingExtension.ts` | ~180 | Processing spinner decoration |
| `editor/extensions/InlineIssueExtension.ts` | ~200 | [PS-42] badge node type |
| `editor/extensions/InlineIssueComponent.tsx` | ~120 | Badge React component |
| `hooks/useIssueExtraction.ts` | ~300 | Extraction state, SSE, dedup, approval |
| `hooks/useIssueSyncListener.ts` | ~100 | Supabase Realtime NoteIssueLink listener |
| `components/ExtractionPreviewModal.tsx` | ~350 | Streaming candidate selection modal |
| `editor/hooks/useSelectionAIActions.ts` | ~200 | Selection toolbar AI actions |
| `editor/hooks/useSelectionContext.ts` | ~100 | Selection position/text context |
| `editor/hooks/useContentUpdates.ts` | ~180 | SSE content update consumer |
| `editor/hooks/contentUpdateHandlers.ts` | ~300 | 10 operation types → TipTap commands |

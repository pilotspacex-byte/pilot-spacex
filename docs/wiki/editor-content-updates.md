# Pilot Space Editor: AI Content Update Pipeline

> **Location**: `frontend/src/features/notes/editor/hooks/`, `backend/src/pilot_space/ai/mcp/`
> **Design Decisions**: DD-088 (MCP Tool Registry), DD-003 (Human-in-the-Loop)

## Overview

When `PilotSpaceAgent` modifies note content via MCP tools (`note_content.update_block`, `note_content.insert_block`, `note_content.delete_block`), those changes must reach the TipTap editor in the browser. The pipeline: MCP handler → DB update → SSE `content_update` event → `useContentUpdates` hook → `contentUpdateHandlers` → TipTap editor command. This is the **AI → Editor** direction; the **Editor → AI** direction is via note sync at conversation start.

---

## Architecture

```
PilotSpaceAgent calls MCP tool:
  note_content.update_block(¶3, "new text", workspace_id)
        ↓
mcp/note_content_server.py
  - resolves ¶3 → UUID via BlockRefMap
  - checks approval tier (DEFAULT → emits approval_request SSE first)
  - on approval: UPDATE blocks SET content=... WHERE id=UUID
        ↓
event_publisher.py
  async with publisher.tool_event(tool_use_id, tool_name):
    result = await execute(payload)
    # emits: tool_result SSE (for ChatView ToolCallCard)
    # emits: content_update SSE (for editor)
        ↓
SSE stream to frontend:
  { type: "content_update", operation: "replace_block",
    blockId: "3f7a2b1c-...", content: "<p>new text</p>",
    expectedContent: "<p>old text</p>", toolUseId: "..." }
        ↓
PilotSpaceStore: onContentUpdate callback fires
        ↓
useContentUpdates (hook in NoteCanvasEditor)
  - event pushed to contentUpdateQueue
  - scheduleFlush() deferred via queueMicrotask()
        ↓
contentUpdateHandlers.applyUpdate(operation, editor)
  - resolves blockId → ProseMirror position via BlockIdExtension
  - executes TipTap command
        ↓
TipTap editor updates DOM (user sees change)
```

---

## 10 Operation Types

All operations are typed via discriminated union in `contentUpdateHandlers.ts`:

| Operation | MCP Tool | TipTap Command |
|-----------|----------|----------------|
| `replace_block` | `note_content.update_block` | `editor.commands.setNodeMarkup()` |
| `insert_after` | `note_content.insert_block` (after) | `editor.commands.insertContentAt(pos+1)` |
| `insert_before` | `note_content.insert_block` (before) | `editor.commands.insertContentAt(pos)` |
| `delete_block` | `note_content.delete_block` | `editor.commands.deleteRange()` |
| `update_attributes` | `note_content.update_block` (attrs only) | `editor.commands.updateAttributes()` |
| `replace_text` | `note_content.update_block` (text range) | `editor.commands.insertContentAt(range)` |
| `insert_text` | `note_content.insert_block` (inline) | `editor.commands.insertContentAt(pos)` |
| `delete_text` | `note_content.delete_block` (text range) | `editor.commands.deleteRange()` |
| `set_heading` | `note_content.update_block` (type) | `editor.commands.setHeading({ level })` |
| `wrap_in_list` | `note_content.update_block` (wrap) | `editor.commands.wrapInList()` |

---

## Block ID Resolution

All MCP operations reference blocks by UUID. The TipTap document uses ProseMirror positions (integers). `BlockIdExtension` maintains the mapping:

```typescript
// BlockIdExtension registers each node's blockId in a Map
const positionMap: Map<string, number> = new Map();

// On every document change, the plugin updates positions:
editor.on('transaction', (tr) => {
  if (!tr.docChanged) return;
  positionMap.clear();
  tr.doc.descendants((node, pos) => {
    if (node.attrs.blockId) {
      positionMap.set(node.attrs.blockId, pos);
    }
  });
});

// contentUpdateHandlers uses:
const pos = BlockIdExtension.getPositionByBlockId(blockId);
if (pos === undefined) {
  // Block was deleted by user; skip this operation silently
  return;
}
```

**Why stable IDs?** ProseMirror positions shift when content is inserted/deleted. A UUID assigned at block creation time stays stable regardless of document changes.

---

## Conflict Detection

For **destructive operations** (`replace_block`, `delete_block`, `replace_text`, `delete_text`):

```typescript
const currentContent = editor.getNodeAtPosition(pos)?.textContent;
const expectedContent = operation.expectedContent;

if (currentContent !== expectedContent) {
  // Conflict: user edited the block after agent started modifying it
  conflictQueue.push({ operation, retryAttempt: 0 });
  scheduleConflictRetry(3000); // First retry in 3 seconds
  return;
}
// No conflict → apply operation immediately
```

**Why `expectedContent`?** The MCP handler captures the block content at the time the tool was called. If the user typed in that block during the 200-500ms between the agent reading and writing, the content will differ. Applying the agent's change would overwrite the user's edit.

**Retry schedule**:
```
Conflict detected at T=0
  → Retry at T=3s (attempt 1)
  → If still conflicted: Retry at T=6s (attempt 2)
  → If still conflicted: Emit SSE conflict_error, abandon operation
```

Maximum 2 retries. After that, the agent is informed via SSE that the operation failed. The agent can then re-read the block and retry with the current content.

**Non-destructive operations bypass conflict detection**: `insert_after`, `insert_before`, `update_attributes` do not check `expectedContent`. These are additive and cannot overwrite user content.

---

## `queueMicrotask()` Deferral

All TipTap command dispatches are deferred:

```typescript
const scheduleFlush = () => {
  queueMicrotask(() => {
    while (contentUpdateQueue.current.length > 0) {
      const operation = contentUpdateQueue.current.shift()!;
      applyUpdate(operation, editor);
    }
  });
};
```

**Why `queueMicrotask()`?** SSE event callbacks fire during browser event processing. TipTap may be in the middle of a transaction (e.g., processing an `input` event) when the SSE callback fires. Deferring to a microtask ensures the current ProseMirror transaction completes before the new one starts, preventing nested transaction errors.

This is the same pattern used in `GhostTextExtension` — a recurring React 19 safety boundary.

---

## ¶N Reference Resolution (Backend Side)

Before any MCP tool call reaches the frontend pipeline, the backend resolves ¶N shorthand to UUIDs:

```python
# mcp/block_ref_map.py
class BlockRefMap:
    def __init__(self, blocks: list[Block]):
        self._map = {f"¶{i+1}": block.id for i, block in enumerate(blocks)}

    def resolve(self, ref: str) -> str:
        if ref.startswith("¶"):
            return self._map.get(ref) or raise ValueError(f"Unknown block ref: {ref}")
        return ref  # Already a UUID
```

The AI can write `update ¶3 to say...` instead of `update 3f7a2b1c-4d5e-6f7a-8b9c-0d1e2f3a4b5c`. The BlockRefMap is rebuilt fresh on each tool call that reads note content.

---

## Approval Before Content Writes

All content-write operations (`replace_block`, `insert_block`, `delete_block`) are `DEFAULT` tier in the MCP registry:

```
Agent calls note_content.update_block
    ↓
PermissionHandler: tier = DEFAULT
    ↓
Emit: approval_request SSE (with ContentDiff payload)
    ↓
Frontend: InlineApprovalCard rendered in ChatView
  Shows: ContentDiff component (before/after diff view)
    ↓
User clicks "Approve" → POST /api/v1/ai/approvals/{id}/approve
    ↓
ApprovalWaiter (backend) detects status change
    ↓
MCP handler proceeds with the actual DB update
    ↓
content_update SSE emitted → reaches TipTap editor
```

**ContentDiff component**: Renders a side-by-side or unified diff of the block content. Deleted text is red, inserted text is green. User can see exactly what the AI intends to change before approving.

---

## Processing Indicator

While the agent is streaming content into a block, `AIBlockProcessingExtension` shows a visual indicator:

```
┌──────────────────────────────────────────────────┐
│ ⟳  This paragraph is being updated by AI...     │  ← processing decoration
└──────────────────────────────────────────────────┘
```

**Lifecycle**:
1. `content_update` SSE received (operation starts) → `setProcessing(blockId)`
2. TipTap command applied → `clearProcessing(blockId)`
3. 300ms "done" animation: green checkmark → fades out

---

## Note → Agent Sync (Initial Direction)

Before starting a conversation, `PilotSpaceAgent` syncs the current note content:

```python
# agents/pilotspace_agent.py
async def _sync_note_context(self, note_id: str) -> None:
    note = await note_repo.get_with_blocks(note_id)
    # Build BlockRefMap for this note
    self.block_ref_map = BlockRefMap(note.blocks)
    # Inject into prompt as "Current note content: ¶1: ..., ¶2: ..."
    self.note_context = self.block_ref_map.format_for_prompt(note.blocks)
```

The agent receives the note content as a formatted string with ¶N references. When it later modifies blocks, it uses the same ¶N references it was given.

---

## Implicit Features

| Feature | Mechanism | File |
|---------|-----------|------|
| Stable block IDs across doc changes | `BlockIdExtension` position map | `extensions/BlockIdExtension.ts` |
| Silent skip on deleted blocks | `pos === undefined` check | `contentUpdateHandlers.ts` |
| Conflict retry (exponential) | 3s → 6s → abandon | `useContentUpdates.ts` |
| Non-destructive bypass conflict check | `operation.type` branching | `contentUpdateHandlers.ts` |
| `queueMicrotask()` safety | Deferred after current transaction | `useContentUpdates.ts` |
| ContentDiff approval UI | Backend sends before/after in payload | `event_publisher.py` |
| Processing indicator on target block | `AIBlockProcessingExtension.setProcessing()` | `AIBlockProcessingExtension.ts` |
| ¶N rebuilt each tool call | `BlockRefMap` is not cached (cheap rebuild) | `mcp/block_ref_map.py` |
| Atomic `tool_use + tool_result` SSE | `asyncio.Lock` in `EventPublisher` | `mcp/event_publisher.py` |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| `queueMicrotask()` before TipTap dispatch | SSE callbacks are async browser events. TipTap may be mid-transaction. Microtask defers to after current task. |
| Conflict detection with `expectedContent` | User typing during agent processing is common (5-10s agent latency). Without check, agent silently overwrites user edits. |
| 2-retry limit on conflicts | After 2 retries (9 seconds total), the user has clearly made a significant change. Agent should re-read and re-attempt if needed. |
| `DEFAULT` approval for all content writes | Content changes are visible to users and affect their work. Approval ensures no surprise edits. (DD-003) |
| ¶N notation (not UUIDs in prompts) | 36-char UUID in LLM prompt = 5 tokens per block reference. ¶N = 2 tokens. In a 10-block note, that's 30 tokens saved per tool call. |
| ContentDiff in approval payload | User must understand what will change before approving. Generic "update block" approval card is insufficient for content changes. |
| `addToHistory: false` for re-insertions | System operations (PropertyBlock re-insert, conflict recovery) should not pollute user's undo history. |

---

## Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `editor/hooks/useContentUpdates.ts` | ~180 | SSE consumer, queue management, microtask deferral |
| `editor/hooks/contentUpdateHandlers.ts` | ~300 | 10 operation type → TipTap command mapping |
| `editor/extensions/BlockIdExtension.ts` | ~150 | Stable UUID → ProseMirror position map |
| `editor/extensions/AIBlockProcessingExtension.ts` | ~180 | Processing spinner decoration |
| `backend/ai/mcp/note_content_server.py` | ~200 | 5 MCP tools: get/update/insert/delete block |
| `backend/ai/mcp/block_ref_map.py` | ~80 | ¶N ↔ UUID resolution |
| `backend/ai/mcp/event_publisher.py` | ~100 | Atomic SSE emission (tool_use + content_update) |

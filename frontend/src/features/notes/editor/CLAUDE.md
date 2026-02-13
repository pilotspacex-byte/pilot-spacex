# Notes Editor - Feature Deep Dives

**File**: `frontend/src/features/notes/editor/CLAUDE.md`
**Scope**: Editor feature details, AI integration patterns, common code examples
**Parent**: [`../CLAUDE.md`](../CLAUDE.md) (Notes Module)

---

## Overview

This document covers the deep-dive implementation details for the note editor's AI-integrated features: ghost text, auto-save, margin annotations, issue extraction, and content updates from AI.

---

## 1. Ghost Text (DD-067)

**SLA**: <2.5s total (500ms pause + 1.5s response + 500ms render)

**Service**: `ghostTextService.ts` (EventSource-based SSE)

**Features**:

- Auto-reconnect on failure (3 attempts, exponential backoff)
- Request cancellation support
- 5s timeout
- Text buffer accumulation
- Code-aware suggestions (Gemini Flash)

**Keyboard Shortcuts**:

- Tab = accept full suggestion
- Right Arrow (at end of line) = accept next word only
- Escape = dismiss

**Example Flow**:

```
User stops typing for 500ms
  -> GhostTextExtension.onTrigger()
  -> SSE POST to /api/v1/ai/ghost-text
  -> Gemini Flash streams tokens
  -> Decoration rendered (faded CSS)
  -> User presses Tab/Right/Escape
```

---

## 2. Auto-Save (useAutoSave hook)

**Generic Hook**: Reusable across app (not note-specific).

**Flow**:

```
Content changed
  -> isDirty = true
  -> Debounce 2s
  -> isSaving = true
  -> onSave() with 3 retry attempts
  -> lastSavedAt = now
  -> Status = "saved" (2s)
  -> Status = "idle"
```

**Retry Logic**: Exponential backoff (1s, 2s, 4s) with 30% jitter

**State**:

- `status`: 'idle' | 'dirty' | 'saving' | 'saved' | 'error'
- `isDirty`: boolean
- `isSaving`: boolean
- `lastSavedAt`: Date | null

---

## 3. Margin Annotations

**Trigger**: 2s pause after editing 50+ characters in a block

**Data Flow**:

1. MarginAnnotationAutoTriggerExtension detects threshold
2. Sends context (block + 3 surrounding blocks) to backend
3. AI agent analyzes and returns annotations (SSE)
4. Frontend renders icons in margin (CSS Anchor Positioning)
5. User clicks to expand in annotation-detail-popover.tsx

**Types**: ambiguity, grammar, abbreviation, clarity

**Confidence Scale**: 0-1 (affects visual prominence)

---

## 4. Issue Extraction

**Endpoint**: `POST /api/v1/ai/notes/:noteId/extract-issues` (SSE streaming)

**Categorization**:

- **Explicit**: Clear actionable items (70%+ confidence)
- **Implicit**: Inferred from context (50-70%)
- **Related**: Loosely connected (30-50%)

**Approval Flow** (DD-003):

1. Backend streams extracted issues
2. Frontend IssueExtractionStore buffers
3. User selects issues to create
4. ApprovalModal shows (non-dismissable, 24h expiry)
5. On approve: Create issues + link via `NoteIssueLink` (EXTRACTED type)

---

## 5. Content Updates from AI

**Operation Types**:

1. **replace_block**: Replace entire block content
2. **append_blocks**: Insert new blocks after cursor
3. **insert_inline_issue**: Create inline issue reference

**Conflict Detection**: If user is editing the target block, retry later (exponential backoff)

**Handler**: `useContentUpdates()` hook + `contentUpdateHandlers.ts` module

---

## 6. PM Block Content Updates

Two operations for AI-initiated PM block management:

**Operation Types**:

1. **insert_pm_block**: Insert a new PM block node (non-destructive, no conflict detection)
2. **update_pm_block**: Update an existing PM block's data attribute (respects edit guard FR-048)

**Data Flow**:

```
Backend SSE content_update event (operation: insert_pm_block/update_pm_block)
  -> PilotSpaceStore.pendingContentUpdates
  -> useContentUpdates hook (MobX reaction)
  -> handleInsertPMBlock / handleUpdatePMBlock (contentUpdateHandlers.ts)
  -> TipTap editor insertContentAt / setNodeMarkup
```

**Edit Guard (FR-048)**: The `useBlockEditGuard` hook tracks user-edited blocks. When `PMBlockNodeView.onDataChange` is called (user edits), the block is marked via `markEdited(blockId)`. The `update_pm_block` handler checks `isBlockEdited()` before applying. If the block was user-edited, the update is silently skipped.

**pmBlockData payload**:

```json
{
  "blockType": "decision",
  "data": "{\"title\":\"...\",\"status\":\"open\",...}",
  "version": 1
}
```

Note: `data` must be a JSON-encoded string, not a raw object.

---

## Common Patterns

### Fetch a Note

```tsx
const {
  data: note,
  isLoading,
  error,
} = useNote({
  workspaceId,
  noteId,
  enabled: !!noteId,
});

if (isLoading) return <NoteDetailSkeleton />;
if (error) return <ErrorBoundary error={error} />;
if (!note) return <NoteNotFound />;

return <NoteCanvas note={note} />;
```

### Auto-Save Setup

```tsx
const { status, isDirty, isSaving } = useAutoSave({
  data: editor.getJSON(),
  onSave: async (content) => {
    await notesApi.update(workspaceId, noteId, { content });
  },
  debounceMs: 2000,
  enabled: !!noteId,
});

return (
  <div className="text-xs text-muted-foreground">
    {status === 'saving' && 'Saving...'}
    {status === 'saved' && 'Saved'}
    {status === 'error' && 'Error saving'}
  </div>
);
```

### Content Updates Listener

```tsx
export function NoteCanvas() {
  const editor = useEditor({ extensions });
  const { pilotSpaceStore } = useStores();

  const { processingBlockIds } = useContentUpdates(editor, pilotSpaceStore, noteId, workspaceId);

  return (
    <>
      <EditorContent editor={editor} />
      {processingBlockIds.map((blockId) => (
        <AIProcessingIndicator key={blockId} blockId={blockId} />
      ))}
    </>
  );
}
```

### Ghost Text Setup

```tsx
const extensions = createEditorExtensions({
  ghostText: {
    enabled: true,
    debounceMs: 500,
    minChars: 10,
    onTrigger: async (context) => {
      const service = getGhostTextService();
      await service.requestCompletion(
        context,
        (chunk) => editor.commands.setGhostText(chunk),
        () => console.log('Done'),
        (err) => console.error(err)
      );
    },
    onAccept: (text, type) => {
      editor.commands.deleteGhostText();
      editor.commands.insertContent(type === 'full' ? text : text.split(/\s+/)[0] + ' ');
    },
  },
});
```

---

## File Organization

```
frontend/src/features/notes/editor/
├── extensions/                          # 13 TipTap extensions
│   ├── BlockIdExtension.ts
│   ├── GhostTextExtension.ts
│   ├── AnnotationMark.ts
│   ├── MarginAnnotationExtension.ts
│   ├── MarginAnnotationAutoTriggerExtension.ts
│   ├── IssueLinkExtension.ts
│   ├── InlineIssueExtension.ts
│   ├── CodeBlockExtension.ts
│   ├── MentionExtension.ts
│   ├── SlashCommandExtension.ts
│   ├── ParagraphSplitExtension.ts
│   ├── AIBlockProcessingExtension.ts
│   ├── LineGutterExtension.ts
│   ├── createEditorExtensions.ts
│   ├── ghost-text-styles.ts
│   ├── ghost-text-widgets.ts
│   ├── index.ts
│   └── MARKDOWN_USAGE.md
├── hooks/
│   ├── useContentUpdates.ts
│   ├── useSelectionContext.ts
│   ├── useSelectionAIActions.ts
│   ├── contentUpdateHandlers.ts
│   ├── config.ts
│   └── index.ts
├── types.ts
├── config.ts
├── CLAUDE.md                            # This file
└── __tests__/
```

---

## Related Documentation

- **Parent Notes Module**: [`../CLAUDE.md`](../CLAUDE.md)
- **Editor Components**: [`../../../components/editor/CLAUDE.md`](../../../components/editor/CLAUDE.md)
- **AI Stores**: [`../../../stores/ai/CLAUDE.md`](../../../stores/ai/CLAUDE.md)
- **Design Decisions**: DD-067 (ghost text), DD-003 (approvals), DD-013 (Note-First)

# Notes Module - Pilot Space

_For project overview and frontend architecture, see main CLAUDE.md and `frontend/CLAUDE.md`_

## Overview

The **notes** module is the core of Pilot Space's Note-First workflow. It provides a sophisticated block-based editor (TipTap + ProseMirror) with 13 extensions, real-time AI assistance (ghost text), auto-save, margin annotations, and seamless integration with the issue extraction pipeline.

**File Path**: `frontend/src/features/notes/`

**Role**: Note Canvas is the home view default. Users start with a collaborative note canvas, not a form. AI acts as an embedded co-writing partner (ghost text, margin annotations, slash commands). Issues emerge naturally from refined thinking, pre-filled with context.

**Key Design Decisions**: DD-013 (Note-First workflow), DD-065 (MobX for UI state), DD-067 (Ghost text: 500ms/50 tokens/code-aware)

---

## Submodule Documentation

| Module                | Doc                                    | Covers                                                                                                           |
| --------------------- | -------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| **Editor Deep-Dives** | [`editor/CLAUDE.md`](editor/CLAUDE.md) | Ghost text, auto-save, margin annotations, issue extraction, content updates, common patterns with code examples |

---

## Architecture Overview

### Component Tree

```
frontend/src/features/notes/
├── components/                              # UI components
│   ├── EditorToolbar.tsx                    # Top toolbar with AI toggles
│   ├── annotation-card.tsx                  # Annotation card display
│   ├── annotation-detail-popover.tsx        # Annotation detail panel
│   ├── margin-annotation-list.tsx           # List of margin annotations
│   └── README.md                            # Issue extraction UI docs
├── editor/                                  # TipTap editor core
│   ├── extensions/                          # 13 TipTap extensions
│   ├── hooks/                               # Editor-specific hooks
│   ├── types.ts                             # TypeScript types
│   ├── config.ts                            # Default config values
│   ├── CLAUDE.md                            # Editor deep-dives
│   └── __tests__/
├── hooks/                                   # Module-level hooks
│   ├── useNote.ts, useNotes.ts              # TanStack Query
│   ├── useCreateNote.ts, useUpdateNote.ts   # Mutations
│   ├── useDeleteNote.ts                     # Delete mutation
│   ├── useAutoSave.ts                       # Auto-save with 2s debounce
│   ├── useIssueSyncListener.ts              # Real-time issue sync
│   └── index.ts
├── services/
│   └── ghostTextService.ts                  # SSE client for ghost text
└── components/index.ts
```

### Key Stores (MobX)

**NoteStore** (`/stores/features/notes/NoteStore.ts`): Current note management, auto-save state tracking, annotations management, ghost text suggestions, dirty state + auto-save reaction (2s debounce).

**PilotSpaceStore** (`/stores/ai/PilotSpaceStore.ts`): Centralized AI conversation state, SSE connection management, content update queue, approval request handling.

**GhostTextStore** (`/stores/ai/GhostTextStore.ts`): Ghost text-specific state, independent of PilotSpaceStore for fast-path (<2.5s SLA).

---

## 16 TipTap Extensions Breakdown

| #   | Extension                                | Purpose                                   | Debounce | Config                              |
| --- | ---------------------------------------- | ----------------------------------------- | -------- | ----------------------------------- |
| 1   | **BlockIdExtension**                     | Assign stable block IDs to all elements   | -        | `preserveOnPaste: true`             |
| 2   | **GhostTextExtension**                   | AI text completions after 500ms pause     | 500ms    | `minChars: 10, maxTokens: 50`       |
| 3   | **AnnotationMark**                       | Highlight text with annotation marks      | -        | CSS: `annotation-mark`              |
| 4   | **MarginAnnotationExtension**            | Render annotation indicators in margin    | -        | CSS Anchor Positioning              |
| 5   | **MarginAnnotationAutoTriggerExtension** | Trigger AI annotations after pause        | 2s       | `minChars: 50, contextBlocks: 3`    |
| 6   | **IssueLinkExtension**                   | Auto-detect `[PS-XX]` with preview        | -        | Regex: `/\[PS-\d+\]/g`              |
| 7   | **InlineIssueExtension**                 | Inline issue references with state colors | -        | Markdown: `[PS-99](issue:uuid)`     |
| 8   | **CodeBlockExtension**                   | Syntax-highlighted code blocks            | -        | `showCopyButton: true`              |
| 9   | **MentionExtension**                     | @mentions for users/notes (optional)      | -        | `trigger: '@', maxSuggestions: 10`  |
| 10  | **SlashCommandExtension**                | /slash commands for actions               | -        | From `slash-command-items.ts`       |
| 11  | **ParagraphSplitExtension**              | Visual block separation on Enter          | -        | `convertDoubleHardBreak: true`      |
| 12  | **AIBlockProcessingExtension**           | Visual indicator on AI processing         | -        | Reads `editor.storage.aiProcessing` |
| 13  | **LineGutterExtension**                  | Line numbers + heading fold/unfold        | -        | `foldableTypes: ['heading']`        |
| 14  | **PMBlockExtension**                     | Generic atom node for PM block types      | -        | `blockType, data, version`          |
| 15  | **TaskItemEnhanced**                     | Enhanced taskItem with metadata attrs     | -        | `assignee, dueDate, priority, etc.` |
| 16  | **ProgressBarDecoration**                | Progress bar above TaskList nodes         | -        | `stateful plugin, map on non-doc`   |

---

## MobX State Patterns

### State Split (DD-065)

**Rule**: MobX = UI state only. TanStack Query = server state.

```tsx
// MobX for UI
class NoteStore {
  @observable selectedBlockId: string | null = null;
  @observable isAnnotationDetailOpen = false;
  @observable isDirty = false;
}

// TanStack Query for server
function useNote(noteId: string) {
  return useQuery({ queryKey: ['notes', noteId], queryFn: () => notesApi.get(noteId) });
}
```

### Component Pattern

All components using MobX must be wrapped with `observer()`:

```tsx
export const NoteList = observer(function NoteList() {
  const { notes } = useStores();
  return (
    <div>
      {notes.filteredNotes.map((note) => (
        <NoteCard key={note.id} note={note} />
      ))}
    </div>
  );
});
```

---

## Integration with AI Features

### SSE Event Flow

```
Backend SSE Event
  -> PilotSpaceStore.handleEvent()
  -> Specific handler (content_update, approval_request, etc.)
  -> Frontend action (useContentUpdates, ApprovalModal, etc.)
  -> MobX update + UI render
```

**Event Types**: message_start, text_delta, tool_use, tool_result, content_update, approval_request, task_progress, message_stop, error

---

## Quality Gates

```bash
cd frontend
pnpm lint && pnpm type-check && pnpm test
```

**Coverage Requirements**: hooks 90%+, services 85%+, editor/hooks 85%+, editor/extensions 70%+, overall >80%

---

## Related Documentation

- **Editor Deep-Dives**: [`editor/CLAUDE.md`](editor/CLAUDE.md) -- Ghost text, auto-save, annotations, issue extraction, common patterns
- **DD-013**: Note-First workflow
- **DD-003**: Human-in-the-loop approval
- **DD-065**: State split (MobX for UI, TanStack Query for server)
- **DD-067**: Ghost text (500ms pause, 50 tokens max, code-aware, Gemini Flash)
- **DD-086**: Centralized agent architecture
- **Dev Patterns**: `docs/dev-pattern/45-pilot-space-patterns.md`
- **Frontend Architecture**: `docs/architect/frontend-architecture.md`

---

## Implementation Checklist

### When Adding TipTap Extension

- [ ] Extends `Extension` class from @tiptap/core
- [ ] Implements lifecycle: `addGlobalAttributes()`, `addCommands()`, `addProseMirrorPlugins()`
- [ ] Exports types + interfaces
- [ ] Unit tests for plugin logic
- [ ] Documented in this CLAUDE.md (added to 13 extensions table)
- [ ] Added to `createEditorExtensions.ts` factory

### When Adding Hook

- [ ] TanStack Query hooks use proper caching keys
- [ ] MobX reactions use `makeAutoObservable` + disposers
- [ ] No blocking I/O in effects or callbacks
- [ ] Cleanup on unmount, export from barrel

### When Integrating with AI

- [ ] Use PilotSpaceStore for all interactions (centralized)
- [ ] Content updates via `useContentUpdates()` hook
- [ ] Approval required for destructive actions (DD-003)
- [ ] Error handling with toast notifications

---

## Troubleshooting

| Issue                        | Steps                                                                     |
| ---------------------------- | ------------------------------------------------------------------------- |
| Ghost Text Not Showing       | Check extension list, 500ms pause, SSE connection, GhostTextStore.enabled |
| Auto-Save Not Triggering     | Verify useAutoSave enabled, onSave callback, dirty detection, network tab |
| Annotations Not Rendering    | Check MarginAnnotationExtension, CSS Anchor support, block ID match       |
| Content Updates Not Applying | Check SSE connection, useContentUpdates hook, operation type, retry queue |

---

## Quick Reference

| Feature          | File                                  | SLA        | Debounce |
| ---------------- | ------------------------------------- | ---------- | -------- |
| Ghost text       | GhostTextExtension                    | <2.5s      | 500ms    |
| Auto-save        | useAutoSave                           | 3-4s total | 2s       |
| Annotations      | MarginAnnotationAutoTriggerExtension  | 2-3s       | 2s       |
| Content updates  | useContentUpdates                     | Real-time  | -        |
| Issue extraction | `/api/v1/ai/notes/:id/extract-issues` | Streaming  | -        |
| Block IDs        | BlockIdExtension                      | Immediate  | -        |

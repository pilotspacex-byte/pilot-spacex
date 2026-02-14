# Notes Module

_For project overview, see main `CLAUDE.md` and `frontend/CLAUDE.md`_

## Purpose

Core of Pilot Space's Note-First workflow (DD-013). Block-based editor (TipTap + ProseMirror) with 16 extensions, real-time AI assistance (ghost text), auto-save, margin annotations, and issue extraction pipeline.

Note Canvas is the home view default. Users start with a collaborative canvas; AI acts as embedded co-writing partner. Issues emerge naturally from refined thinking.

**Design Decisions**: DD-013 (Note-First), DD-065 (state split), DD-067 (ghost text)

**Editor deep-dives**: See [`editor/CLAUDE.md`](editor/CLAUDE.md)

---

## Directory Structure

```
frontend/src/features/notes/
├── components/
│   ├── EditorToolbar.tsx                    # Top toolbar with AI toggles
│   ├── annotation-card.tsx
│   ├── annotation-detail-popover.tsx
│   └── margin-annotation-list.tsx
├── editor/                                  # TipTap editor core
│   ├── extensions/                          # 16 TipTap extensions
│   ├── hooks/                               # Editor-specific hooks
│   ├── types.ts, config.ts
│   └── CLAUDE.md                            # Editor deep-dives
├── hooks/
│   ├── useNote.ts, useNotes.ts              # TanStack Query
│   ├── useCreateNote.ts, useUpdateNote.ts, useDeleteNote.ts
│   ├── useAutoSave.ts                       # 2s debounce
│   ├── useIssueSyncListener.ts
│   └── index.ts
├── services/
│   └── ghostTextService.ts                  # SSE client for ghost text
└── components/index.ts
```

---

## Key Stores (MobX)

- **NoteStore** (`stores/features/notes/NoteStore.ts`): Current note, auto-save state, annotations, ghost text suggestions, dirty state.
- **PilotSpaceStore** (`stores/ai/PilotSpaceStore.ts`): AI conversation, SSE connection, content update queue, approvals.
- **GhostTextStore** (`stores/ai/GhostTextStore.ts`): Ghost text state, independent of PilotSpaceStore for fast-path (<2.5s SLA).

---

## 16 TipTap Extensions

| # | Extension | Purpose | Debounce | Config |
|---|-----------|---------|----------|--------|
| 1 | BlockIdExtension | Stable block IDs | - | `preserveOnPaste: true` |
| 2 | GhostTextExtension | AI completions after pause | 500ms | `minChars: 10, maxTokens: 50` |
| 3 | AnnotationMark | Highlight with annotation marks | - | CSS: `annotation-mark` |
| 4 | MarginAnnotationExtension | Annotation indicators in margin | - | CSS Anchor Positioning |
| 5 | MarginAnnotationAutoTriggerExtension | AI annotations after pause | 2s | `minChars: 50, contextBlocks: 3` |
| 6 | IssueLinkExtension | Auto-detect `[PS-XX]` with preview | - | Regex: `/\[PS-\d+\]/g` |
| 7 | InlineIssueExtension | Inline issue refs with state colors | - | Markdown: `[PS-99](issue:uuid)` |
| 8 | CodeBlockExtension | Syntax-highlighted code | - | `showCopyButton: true` |
| 9 | MentionExtension | @mentions for users/notes | - | `trigger: '@', maxSuggestions: 10` |
| 10 | SlashCommandExtension | /slash commands | - | From `slash-command-items.ts` |
| 11 | ParagraphSplitExtension | Block separation on Enter | - | `convertDoubleHardBreak: true` |
| 12 | AIBlockProcessingExtension | Visual indicator on AI processing | - | Reads `editor.storage.aiProcessing` |
| 13 | LineGutterExtension | Line numbers + heading fold | - | `foldableTypes: ['heading']` |
| 14 | PMBlockExtension | Atom node for PM block types | - | `blockType, data, version` |
| 15 | TaskItemEnhanced | Enhanced taskItem with metadata | - | `assignee, dueDate, priority` |
| 16 | ProgressBarDecoration | Progress bar above TaskList nodes | - | Stateful plugin |

All instantiated via `createEditorExtensions()` factory. See `editor/extensions/`.

---

## SSE Event Flow

```
Backend SSE Event
  -> PilotSpaceStore.handleEvent()
  -> Specific handler (content_update, approval_request, etc.)
  -> Frontend action (useContentUpdates, ApprovalModal, etc.)
  -> MobX update + UI render
```

**Event Types**: message_start, text_delta, tool_use, tool_result, content_update, approval_request, task_progress, message_stop, error.

---

## Quick Reference

| Feature | File | SLA | Debounce |
|---------|------|-----|----------|
| Ghost text | GhostTextExtension | <2.5s | 500ms |
| Auto-save | useAutoSave | 3-4s total | 2s |
| Annotations | MarginAnnotationAutoTriggerExtension | 2-3s | 2s |
| Content updates | useContentUpdates | Real-time | - |
| Issue extraction | `/api/v1/ai/notes/:id/extract-issues` | Streaming | - |

---

## Troubleshooting

| Issue | Steps |
|-------|-------|
| Ghost Text Not Showing | Check extension list, 500ms pause, SSE connection, GhostTextStore.enabled |
| Auto-Save Not Triggering | Verify useAutoSave enabled, onSave callback, dirty detection |
| Annotations Not Rendering | Check MarginAnnotationExtension, CSS Anchor support, block ID match |
| Content Updates Not Applying | Check SSE connection, useContentUpdates hook, operation type |

---

## Related Documentation

- **Editor deep-dives**: [`editor/CLAUDE.md`](editor/CLAUDE.md)
- `docs/dev-pattern/45-pilot-space-patterns.md`
- `docs/architect/frontend-architecture.md`

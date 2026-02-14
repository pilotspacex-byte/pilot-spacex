# Notes Editor - Feature Deep Dives

**Parent**: [`../CLAUDE.md`](../CLAUDE.md) (Notes Module)

---

## Purpose

Implementation details for the note editor's AI-integrated features: ghost text, auto-save, margin annotations, issue extraction, and content updates from AI.

---

## 1. Ghost Text (DD-067)

**SLA**: <2.5s total (500ms pause + 1.5s response + 500ms render)

**Service**: `ghostTextService.ts` (EventSource-based SSE, auto-reconnect 3 attempts, 5s timeout, code-aware via Gemini Flash).

**Keyboard**: Tab (accept full), Right Arrow at EOL (accept next word), Escape (dismiss).

**Flow**: User stops typing 500ms -> GhostTextExtension.onTrigger() -> SSE POST -> Gemini Flash streams -> decoration rendered (faded CSS) -> user accepts/dismisses.

**Setup**: See `extensions/createEditorExtensions.ts` for ghost text configuration.

---

## 2. Auto-Save

**Hook**: `useAutoSave` (generic, reusable across app).

**Flow**: Content changed -> isDirty -> 2s debounce -> isSaving -> onSave() with 3 retries (exponential backoff 1s/2s/4s + 30% jitter) -> lastSavedAt -> status cycle (idle/dirty/saving/saved/error).

**Implementation**: See `../hooks/useAutoSave.ts`.

---

## 3. Margin Annotations

**Trigger**: 2s pause after editing 50+ characters in a block.

**Flow**: MarginAnnotationAutoTriggerExtension detects threshold -> sends context (block + 3 surrounding) to backend -> AI returns annotations (SSE) -> margin icons rendered (CSS Anchor Positioning) -> click expands in `annotation-detail-popover.tsx`.

**Types**: ambiguity, grammar, abbreviation, clarity. **Confidence**: 0-1 scale (affects visual prominence).

---

## 4. Issue Extraction

**Endpoint**: `POST /api/v1/ai/notes/:noteId/extract-issues` (SSE streaming)

**Categories**: Explicit (70%+ confidence), Implicit (50-70%), Related (30-50%).

**Approval Flow (DD-003)**: Backend streams extracted issues -> IssueExtractionStore buffers -> user selects -> ApprovalModal (non-dismissable, 24h expiry) -> on approve: create issues + NoteIssueLink (EXTRACTED type).

---

## 5. Content Updates from AI

**Operations**: `replace_block` (replace entire block), `append_blocks` (insert after cursor), `insert_inline_issue` (inline issue ref).

**Conflict Detection**: If user editing target block, retry later (exponential backoff).

**Handler**: `hooks/useContentUpdates.ts` + `hooks/contentUpdateHandlers.ts`.

---

## 6. PM Block Content Updates

**Operations**: `insert_pm_block` (non-destructive, no conflict detection), `update_pm_block` (respects edit guard FR-048).

**Flow**: SSE content_update event -> PilotSpaceStore.pendingContentUpdates -> useContentUpdates hook -> handleInsertPMBlock / handleUpdatePMBlock -> TipTap editor commands.

**Edit Guard (FR-048)**: `useBlockEditGuard` hook tracks user-edited blocks. On `PMBlockNodeView.onDataChange`, block is marked via `markEdited(blockId)`. The `update_pm_block` handler checks `isBlockEdited()` before applying; if user-edited, update is silently skipped.

**pmBlockData payload**: `{ blockType: "decision", data: "{\"title\":\"...\",\"status\":\"open\",...}", version: 1 }`. Note: `data` must be a JSON-encoded string.

---

## File Organization

```
frontend/src/features/notes/editor/
├── extensions/                          # 16 TipTap extensions
│   ├── BlockIdExtension.ts
│   ├── GhostTextExtension.ts
│   ├── AnnotationMark.ts
│   ├── MarginAnnotation*.ts             # Extension + AutoTrigger
│   ├── IssueLinkExtension.ts
│   ├── InlineIssueExtension.ts
│   ├── CodeBlockExtension.ts
│   ├── MentionExtension.ts
│   ├── SlashCommandExtension.ts
│   ├── ParagraphSplitExtension.ts
│   ├── AIBlockProcessingExtension.ts
│   ├── LineGutterExtension.ts
│   ├── createEditorExtensions.ts        # Factory
│   ├── ghost-text-styles.ts, ghost-text-widgets.ts
│   └── index.ts
├── hooks/
│   ├── useContentUpdates.ts
│   ├── useSelectionContext.ts
│   ├── useSelectionAIActions.ts
│   ├── contentUpdateHandlers.ts
│   └── index.ts
├── types.ts, config.ts
└── __tests__/
```

---

## Related Documentation

- **Parent**: [`../CLAUDE.md`](../CLAUDE.md)
- **Editor Components**: `components/editor/CLAUDE.md`
- **AI Stores**: `stores/ai/CLAUDE.md`
- **DD-067** (ghost text), **DD-003** (approvals), **DD-013** (Note-First)

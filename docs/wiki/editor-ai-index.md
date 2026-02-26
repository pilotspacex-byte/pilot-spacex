# Pilot Space: Agent × TipTap Editor Integration Wiki

> **Root locations**: `frontend/src/features/notes/editor/`, `frontend/src/features/issues/editor/`
> **Core design decisions**: DD-003 (Approval), DD-011 (Provider Routing), DD-013 (Note-First), DD-086 (Centralized Agent)

## Overview

Pilot Space embeds AI directly inside two TipTap-based editors: the **Note Canvas** (the home screen) and the **Issue Detail** editor. The AI is not a chat-only overlay — it lives within the editor as ghost text completions, margin annotations, extraction highlights, and AI-generated block content. The `PilotSpaceAgent` and `GhostTextService` (independent path) coordinate with TipTap through a strict React 19-safe boundary, ProseMirror decorations, and MCP tool-driven content updates.

---

## Feature Documents

| Document | What it covers |
|----------|----------------|
| [Ghost Text](./editor-ghost-text.md) | 500ms typing pause → Gemini Flash → inline completions at 40% opacity; Tab/Right Arrow/Escape |
| [Margin Annotations](./editor-margin-annotations.md) | 2000ms pause → AI detects ambiguous text → margin question cards; 5 annotation states |
| [Issue Extraction & Slash Commands](./editor-issue-extraction.md) | `\extract-issues` → SSE modal → NoteIssueLink(EXTRACTED) → `[PS-42]` inline badges |
| [Issue Detail Editor + AI](./editor-issue-detail.md) | PropertyBlockNode, context bridge, auto-save, AI chat panel, approval workflow |
| [AI Content Update Pipeline](./editor-content-updates.md) | MCP `note_content.*` tools → SSE → TipTap editor; 10 operation types, conflict detection |

---

## System Architecture

```
Note Canvas Editor (TipTap)              Issue Detail Editor (TipTap)
┌────────────────────────────────┐      ┌────────────────────────────────┐
│ Extensions:                    │      │ Extensions:                    │
│  GhostTextExtension            │      │  PropertyBlockNode             │
│   └─ ghost-text-widgets        │      │   └─ 2 ProseMirror guards      │
│  MarginAnnotationExtension     │      │   └─ ReactNodeViewRenderer     │
│  MarginAnnotationAutoTrigger   │      │       → PropertyBlockView(obs) │
│  AnnotationMark                │      │  + all note canvas extensions  │
│  AIBlockProcessingExtension    │      └────────────────────────────────┘
│  SlashCommandExtension         │               │
│  InlineIssueExtension          │      Context Bridge
└────────────────────────────────┘      IssueNoteContext.Provider
            │                                    │
            │              PilotSpaceAgent (backend orchestrator)
            │                       │
  ┌─────────┴──────────┐    ┌───────┴────────┐
  │ GhostTextService   │    │ MCP note_content│
  │ (independent path) │    │ tools (via SDK) │
  │ Gemini Flash       │    │ update_block    │
  │ POST /ghost-text   │    │ insert_block    │
  │ <2.5s SLA          │    │ delete_block    │
  └────────────────────┘    └────────────────┘
            │                       │
    GhostTextStore           useContentUpdates hook
    (MobX, LRU cache)        (SSE event queue)
            │                       │
    ProseMirror decoration   TipTap editor command
    (local-only, 40% opacity) (setNodeAttribute, insertContent, etc.)
```

---

## Key Flows

### 1. Ghost Text (Independent Path)

```
User types → 500ms debounce → GhostTextExtension builds context
    ↓
POST /api/v1/ai/ghost-text (Gemini Flash, bypasses PilotSpaceAgent)
    ↓
Response (confidence ≥0.5) → GhostTextStore (LRU cache, MobX)
    ↓
MobX reaction → GhostTextExtension.setGhostText()
    ↓
ProseMirror decoration (widget, 40% opacity)
    ↓
Tab → accept full | Right Arrow → accept word | Escape → dismiss
```

### 2. Margin Annotation (AI-Detected Ambiguity)

```
User pauses 2000ms → MarginAnnotationAutoTriggerExtension
    ↓
Collect 3-block context (≥50 chars) → POST /api/v1/ai/annotations (SSE)
    ↓
AnnotationStore streams annotation objects (MobX runInAction)
    ↓
MarginAnnotationExtension → AnnotationMark applied to text range
    ↓
margin-annotation-list.tsx positions cards via RAF-batched getBoundingClientRect()
    ↓
User responds → annotation-card.tsx dispatches AI action (create issue / send to chat / dismiss)
```

### 3. Issue Extraction (Note → Issues)

```
User types \extract-issues or selects text → SlashCommandExtension
    ↓
ExtractionPreviewModal opens → POST /api/v1/ai/extract-issues (SSE)
    ↓
Streams IssueCandidate[] with confidence scores
    ↓
User selects + approves (DD-003) → POST bulk_create_issues
    ↓
Backend: creates issues + NoteIssueLink(EXTRACTED) records
    ↓
useIssueSyncListener receives Supabase Realtime event
    ↓
InlineIssueExtension renders [PS-42] badges on source text
    ↓
Rainbow-border CSS wraps the extracted text range
```

### 4. MCP Content Update (Agent → TipTap)

```
PilotSpaceAgent calls MCP tool: note_content.update_block(¶3, "new text")
    ↓
MCP handler resolves ¶N → UUID → executes DB update
    ↓
SSE event: { type: "content_update", operation: "replace", blockId, content }
    ↓
useContentUpdates hook dequeues → contentUpdateHandlers.applyUpdate()
    ↓
TipTap editor.commands.updateAttributes() or setContent()
    ↓
AIBlockProcessingExtension shows processing indicator while streaming
    ↓
ContentDiff SSE event → approval card before destructive update (DD-003)
```

### 5. Issue Detail AI Chat (PilotSpaceAgent)

```
IssueDetailPage initializes: store.setIssueContext({ issueId })
    ↓
User opens chat panel → ChatView (lazy Suspense)
    ↓
PilotSpaceAgent receives messages with issue context injected
    ↓
Agent reads issue/modifies via MCP tools (issue.update_issue, etc.)
    ↓
Agent dispatches window.CustomEvent('pilot:issue-updated', { issueId })
    ↓
IssueDetailPage refetches → setEditorKey++ → IssueEditorContent remounts
    ↓
Fresh descriptionHtml rendered; PropertyBlockView reads updated context
```

---

## React 19 + MobX + TipTap Constraint

**The rule**: `IssueEditorContent` MUST NOT be wrapped with `observer()`.

**Why**: MobX `observer()` uses React 19's `useSyncExternalStore`, which calls `flushSync()`. TipTap's `ReactNodeViewRenderer` runs inside ProseMirror transactions during React's render phase. React 19 throws `"flushSync was called from inside a lifecycle method"` when both happen simultaneously.

**Solution — Context Bridge Pattern**:

```
IssueDetailPage (observer)         ← MobX reactivity here
  └── IssueNoteContext.Provider     ← data tunneled via context
       └── IssueEditorContent       ← plain component, NO observer()
            └── PropertyBlockView  ← observer() safe here (child of transaction)
```

This pattern also applies anywhere `ReactNodeViewRenderer` is used inside a MobX-observed component tree.

---

## Editor-AI Integration Points Summary

| Integration | Editor | Trigger | AI Path | UI Output |
|-------------|--------|---------|---------|-----------|
| Ghost text | Note Canvas | 500ms typing pause | GhostTextService (Gemini Flash) | Inline decoration 40% opacity |
| Margin annotations | Note Canvas | 2000ms typing pause | AnnotationService (Sonnet) | Margin question cards |
| Issue extraction | Note Canvas | `\extract-issues` slash cmd | PilotSpaceAgent skill | ExtractionPreviewModal + rainbow borders |
| Selection AI actions | Note Canvas | Text selection | PilotSpaceAgent | Floating toolbar with AI actions |
| Slash commands | Note Canvas | `/` then command name | Various skills | Inline content insertion |
| MCP block updates | Note Canvas | Agent MCP tool call | PilotSpaceAgent → MCP | Content update with approval |
| AI description gen | Issue Detail | "Generate with AI" CTA | PilotSpaceAgent chat | Description populated via `pilot:issue-updated` |
| Task decomposition | Issue Detail | "Decompose into tasks" | PilotSpaceAgent skill | TaskProgressWidget in editor |
| Property mutations | Issue Detail | PropertyBlockView UI | PilotSpaceAgent MCP | `issue.update_issue` → `pilot:issue-updated` |
| Approval overlays | Both | MCP tool tier check | DD-003 | InlineApprovalCard / DestructiveApprovalModal |

---

## Security in AI ↔ Editor Layer

| Layer | Enforcement |
|-------|-------------|
| Block ID ¶N resolution | Validates block belongs to note owned by workspace |
| MCP `note_content.*` | 3-layer RLS (session var + WHERE + DB policy) |
| Approval before writes | DEFAULT tier for all content mutations (DD-003) |
| Sandbox isolation | Agent reads/writes only `/sandbox/{userId}/{workspaceId}/` |
| Rate limiting | Ghost text: 10 req/sec/user (Redis sliding window) |
| Content deduplication | Extraction: 500ms window prevents duplicate issue creation |

---

## Files at a Glance

```
frontend/src/features/notes/editor/extensions/
├── GhostTextExtension.ts           ← ghost text TipTap extension (519 lines)
├── ghost-text-widgets.ts           ← ProseMirror widget decorations
├── ghost-text-styles.ts            ← 40% opacity CSS
├── MarginAnnotationExtension.ts    ← annotation mark renderer
├── MarginAnnotationAutoTriggerExtension.ts ← 2000ms debounce trigger
├── AnnotationMark.ts               ← ProseMirror mark type
├── AIBlockProcessingExtension.ts   ← AI streaming block indicators
├── SlashCommandExtension.ts        ← / command menu
├── slash-command-items.ts          ← all command definitions
├── InlineIssueExtension.ts         ← [PS-42] badge rendering
└── createEditorExtensions.ts       ← full extension registry

frontend/src/features/notes/
├── services/ghostTextService.ts    ← SSE client for ghost text
├── hooks/useIssueExtraction.ts     ← extraction state + API
├── hooks/useIssueSyncListener.ts   ← realtime NoteIssueLink sync
├── components/ExtractionPreviewModal.tsx ← issue selection UI
├── components/annotation-card.tsx  ← margin AI question card
├── components/margin-annotation-list.tsx ← RAF-positioned list
└── editor/hooks/
    ├── useContentUpdates.ts        ← MCP update event consumer
    ├── contentUpdateHandlers.ts    ← 10 operation type handlers
    └── useSelectionAIActions.ts    ← selection → AI floating toolbar

frontend/src/features/issues/
├── editor/property-block-extension.ts   ← PropertyBlockNode + 2 guards
├── editor/create-issue-note-extensions.ts ← issue editor extension set
├── contexts/issue-note-context.ts       ← context bridge type
├── components/issue-editor-content.tsx  ← TipTap mount (NOT observer)
├── components/property-block-view.tsx   ← expanded props (observer)
├── components/property-block-collapsed.tsx ← collapsed chips (observer)
├── components/issue-description-empty-state.tsx ← AI CTA
├── components/issue-chat-empty-state.tsx ← 4 command cards
├── components/task-progress-widget.tsx  ← AI decomposition progress
└── components/suggested-prompts.tsx     ← preset AI prompts
```

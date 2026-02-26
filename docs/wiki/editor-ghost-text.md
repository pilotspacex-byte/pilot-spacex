# Pilot Space Editor: Ghost Text

> **Location**: `frontend/src/features/notes/editor/extensions/GhostTextExtension.ts`, `frontend/src/features/notes/services/ghostTextService.ts`, `frontend/src/stores/GhostTextStore.ts`
> **Design Decisions**: DD-011 (Provider Routing — Gemini Flash for <2.5s), DD-013 (Note-First)

## Overview

Ghost text provides **inline AI completions** while users write in the Note Canvas. After a 500ms typing pause, the system predicts what the user intends to write next and shows the suggestion at 40% opacity directly in the editor. The user can accept it with Tab, accept word-by-word with Right Arrow, or dismiss with Escape. This path **bypasses PilotSpaceAgent entirely** — it goes directly to Gemini Flash via a dedicated endpoint for <2.5s total latency.

---

## Architecture

```
User types in Note Canvas editor
        ↓
GhostTextExtension (TipTap, ProseMirror plugin)
  - 500ms debounce timer
  - builds context: blockType + prefix (200 chars) + surrounding (500 chars)
  - double-newline guard (disabled during slash commands)
        ↓
ghostTextService.fetchGhostText(request)
  POST /api/v1/ai/ghost-text
        ↓
Backend: GhostTextService (ghost_text.py)
  - Rate limit: 10 req/sec/user (Redis sliding window)
  - Cache lookup (Redis, 1h TTL, keyed by content hash)
  - Gemini Flash inference (<1.5s inference SLA)
  - Returns: { suggestion, confidence, tokens }
        ↓
GhostTextStore (MobX)
  - 10-entry LRU cache (keyed by blockId + blockType)
  - Confidence threshold: ≥0.5 to display
  - Observable: suggestion, isLoading, error
        ↓
MobX reaction → GhostTextExtension.setGhostText()
  ↓ queueMicrotask() ← avoids React 19 flushSync conflict
  ↓
ProseMirror decoration (widget, 40% opacity)
  - ghost-text-widgets.ts: creates DOM element
  - ghost-text-styles.ts: opacity: 0.5, pointer-events: none
        ↓
User input:
  Tab       → acceptGhostText() → insertContent() full suggestion
  Right Arrow → acceptNextWord() → insert first word only
  Escape    → dismissGhostText() → remove decoration
  Any other key → auto-clear (stale suggestion guard)
```

---

## Components

### `GhostTextExtension.ts` (519 lines) — TipTap Extension

**Responsibility**: All TipTap-side ghost text logic: debouncing, context extraction, decoration management, keyboard handling.

**ProseMirror plugin state**:
```typescript
{
  suggestion: string | null;
  decorationSet: DecorationSet;
}
```

**Debounce mechanism**: `setTimeout(500ms)` cleared on every `update` transaction. A new request is only sent if:
1. The cursor has text content before it (no empty block trigger)
2. No double-newline in the last 20 chars (slash command guard)
3. Current block type is not `codeBlock` or `horizontalRule`

**Context building**:
- `blockType`: current ProseMirror node type name (used by backend for block-type-aware prompts)
- `prefix`: last 200 characters before cursor position
- `surrounding`: up to 500 characters from adjacent blocks for context

**`queueMicrotask()` pattern**: When the MobX store triggers a reaction to set ghost text, it defers the TipTap dispatch via `queueMicrotask()`. This prevents React 19's `flushSync` from being called during ProseMirror's rendering cycle.

**Keyboard intercept**:
```typescript
addKeyboardShortcuts() {
  return {
    Tab: () => this.acceptGhostText(),
    ArrowRight: () => this.acceptNextWord(),
    Escape: () => this.dismissGhostText(),
  };
}
```

**Collaborative editing (Yjs)**: Ghost text decorations are **local-only**. They use `DecorationSet.map(mapping)` to follow document changes (including remote Yjs changes) so the ghost text stays at the cursor. But the decoration itself is never added to the Yjs doc — peers never see another user's ghost text.

---

### `ghost-text-widgets.ts` (139 lines) — ProseMirror Widget

**Responsibility**: Creates the DOM element for the inline suggestion display.

```typescript
export function createGhostTextWidget(text: string): Decoration {
  const dom = document.createElement('span');
  dom.className = 'ghost-text-suggestion';
  dom.setAttribute('aria-hidden', 'true');
  dom.textContent = text;
  return Decoration.widget(position, () => dom, { side: 1 });
}
```

- `side: 1` places the widget **after** the cursor, not before
- `aria-hidden: true` — screen readers ignore ghost text (not committed content)
- Decoration is a widget (inline element), not a node decoration

---

### `ghost-text-styles.ts` (94 lines) — CSS Variables

```typescript
export const ghostTextStyles = css`
  .ghost-text-suggestion {
    opacity: 0.5;           /* Perceptually 40% — distinguishable from real text */
    pointer-events: none;   /* Click-through — user can click past it */
    color: var(--foreground); /* Same color as real text, distinguishable by opacity only */
    white-space: pre;       /* Preserve spaces and newlines in suggestion */
    user-select: none;      /* Cannot be selected/copied */
  }
`;
```

**Why 40% opacity?** Perceptually low enough to not distract from actual writing, high enough to read without effort. At 20% it becomes invisible; at 70% users confuse it for committed text.

---

### `GhostTextStore.ts` (217 lines) — MobX Store

**Responsibility**: Manages ghost text state globally, including caching and fetch lifecycle.

**Observable state**:
```typescript
@observable suggestion: string | null = null;
@observable isLoading: boolean = false;
@observable error: string | null = null;
@observable private cache: Map<string, CachedSuggestion> = new Map(); // 10-entry LRU
```

**Cache key**: `${noteId}:${blockId}:${blockType}` — per-block, per-type.

**10-entry LRU**: When cache exceeds 10, the oldest entry (by insertion order) is evicted. Prevents memory growth for long notes.

**Confidence threshold**: Suggestions with `confidence < 0.5` are stored in cache but not shown to the user. Prevents low-quality completions from interrupting flow.

**Rate limiting coordination**: The store tracks `lastRequestTime` to enforce minimum 100ms between requests, supplementing the 500ms debounce for cases where the user is moving the cursor rapidly.

---

### `ghostTextService.ts` (Notes feature) — SSE Client

**Responsibility**: HTTP client that calls the ghost text endpoint.

```typescript
async fetchGhostText(request: GhostTextRequest): Promise<GhostTextResponse> {
  const response = await fetch('/api/v1/ai/ghost-text', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      workspace_id: request.workspaceId,
      note_id: request.noteId,
      block_type: request.blockType,
      prefix: request.prefix.slice(-200),         // Last 200 chars
      surrounding_context: request.context.slice(0, 500), // First 500 chars
    }),
    signal: AbortSignal.timeout(3000),  // 3s timeout (SLA is <2.5s)
  });
  return response.json();
}
```

**Why JSON POST, not SSE?** Ghost text is returned as a single complete suggestion, not a stream. Streaming tokens into an inline decoration creates visual noise (each token render shifts the cursor position). A single atomic response is cleaner.

---

## Backend: `ghost_text.py` (224 lines)

**Path**: `backend/src/pilot_space/ai/services/ghost_text.py`

| Layer | Detail |
|-------|--------|
| Model | Gemini Flash (via DD-011 ProviderSelector) |
| Rate limit | 10 requests/sec/user (Redis sliding window, `rate_limiter.py`) |
| Cache | Redis, 1h TTL, keyed by SHA256(prefix+context+blockType) |
| Prompt | Block-type-aware: paragraph prompt ≠ heading prompt ≠ list item prompt |
| Inference | Non-streaming completion with max_tokens=150 |
| Response | `{ suggestion: string, confidence: float, input_tokens: int, output_tokens: int }` |
| Fallback | On Redis outage: proceeds without cache (fail-open for ghost text) |

**Block-type-aware prompts**: Heading blocks get completions that match heading style (concise, capitalized). Paragraph blocks get sentence continuations. List item blocks suggest list-item-appropriate completions. This prevents the model from suggesting a paragraph-length completion inside a bullet point.

---

## Key Interactions

### With Collaborative Editing (Yjs)

```
Remote user inserts text at position 50
        ↓
YjsCollabExtension applies Yjs transaction
        ↓
GhostTextExtension's state.apply() is called
        ↓
DecorationSet.map(transaction.mapping) shifts ghost text position
        ↓
Ghost text stays at local cursor (not at remote insert position)
```

The decoration mapping ensures ghost text follows the cursor through remote edits. If a remote edit deletes the cursor's paragraph, the ghost text decoration is removed (mapped to null position).

### With Slash Commands

```
User types "/" in editor
        ↓
SlashCommandExtension activates menu
        ↓
GhostTextExtension: double-newline check detects slash command context
        ↓
Ghost text fetch is suppressed until slash command resolves
```

Detection: checks if last 20 chars contain `\n\n` or if cursor is at position after `/`. This prevents ghost text from competing visually with the slash command menu.

### Accept Word-by-Word

```
Suggestion: "implement authentication middleware for"
Right Arrow pressed once:
  → accepts "implement" (up to next space)
  → remaining suggestion: " authentication middleware for"
  → shown as new decoration
Right Arrow pressed again:
  → accepts "authentication" ...
Tab pressed:
  → accepts entire remaining suggestion
```

---

## Implicit Features

| Feature | Mechanism | File |
|---------|-----------|------|
| Stale suggestion guard | `editor.on('update')` clears decoration on next keypress | `GhostTextExtension.ts` |
| Block-type awareness | `blockType` sent with request → different prompts | `ghost_text.py` |
| Cursor position tracking through remote edits | `DecorationSet.map()` | `GhostTextExtension.ts` |
| 10-entry LRU cache | Map eviction by insertion order | `GhostTextStore.ts` |
| React 19 flushSync avoidance | `queueMicrotask()` before TipTap dispatch | `GhostTextExtension.ts` |
| Local-only decorations | Never added to Yjs doc | `GhostTextExtension.ts` |
| Abort on new request | `AbortController` cancels in-flight fetch | `ghostTextService.ts` |
| Confidence gating | `confidence < 0.5` → not displayed | `GhostTextStore.ts` |
| aria-hidden decoration | Screen readers ignore ghost text | `ghost-text-widgets.ts` |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Independent path (bypasses PilotSpaceAgent) | PilotSpaceAgent adds ~200ms overhead. Ghost text SLA is <2.5s. Direct service path is required. |
| Gemini Flash, not Claude | Flash: <1s inference for completion tasks. Claude Haiku is an alternative; Flash has lower latency. |
| 500ms debounce (fixed) | 300ms = too frequent, interrupts fast typists. 700ms = noticeable lag. 500ms is the industry standard (GitHub Copilot). |
| JSON POST, not SSE | Single atomic suggestion renders cleanly. Streaming tokens shifts cursor decoration on each token. |
| Local-only decorations | Ghost text is ephemeral UX. Syncing it to peers would create confusing shared suggestions. |
| Tab = full, Right Arrow = word | Full accept (Tab) for high-confidence agreement; word-by-word (Right Arrow) for partial agreement. |
| 40% opacity | Distinguishable from real text without being distracting; matches Apple and GitHub Copilot conventions. |
| Block-type-aware backend prompts | A heading completion should be a phrase; a list item completion should be an item. One-size-fits-all degrades quality. |

---

## Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `editor/extensions/GhostTextExtension.ts` | 519 | TipTap extension: debounce, context, decorations, keyboard |
| `editor/extensions/ghost-text-widgets.ts` | 139 | ProseMirror widget DOM creation |
| `editor/extensions/ghost-text-styles.ts` | 94 | CSS: 40% opacity, pointer-events, aria-hidden |
| `services/ghostTextService.ts` | ~120 | HTTP POST client to ghost text endpoint |
| `stores/GhostTextStore.ts` | 217 | MobX: state, 10-LRU cache, confidence filter |
| `backend/ai/services/ghost_text.py` | 224 | Rate limit, Redis cache, Gemini Flash, block-type prompts |

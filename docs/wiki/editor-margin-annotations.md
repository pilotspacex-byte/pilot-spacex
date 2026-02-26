# Pilot Space Editor: Margin Annotations

> **Location**: `frontend/src/features/notes/editor/extensions/`, `frontend/src/features/notes/components/`
> **Design Decisions**: DD-003 (Human-in-the-Loop), DD-013 (Note-First — AI as co-writing partner)

## Overview

Margin Annotations are **AI-detected ambiguities and improvement suggestions** shown as question cards in the right margin of the Note Canvas. After 2000ms of typing inactivity, the system analyzes the note for unclear text, missing context, or action items — and shows cards alongside the relevant text block. Users can respond by creating an issue, sending the annotation to the AI chat, or dismissing it. This is the "AI as co-writing partner" feature (DD-013), not just autocomplete.

---

## Architecture

```
User pauses typing for 2000ms
        ↓
MarginAnnotationAutoTriggerExtension
  - checks: context length ≥50 chars
  - builds: 3-block surrounding context
  - guards: only triggers on paragraph/heading blocks
        ↓
POST /api/v1/ai/annotations (SSE stream)
  - backend detects ambiguous/actionable text
  - streams annotation objects incrementally
        ↓
AnnotationStore (MobX)
  - receives streaming annotations via runInAction()
  - 5-minute cache per note (prevents re-triggering same content)
  - state machine: detected → loading → shown → dismissed | resolved
        ↓
MarginAnnotationExtension
  - applies AnnotationMark to text range in ProseMirror
  - mark data: annotationId, color, type
        ↓
margin-annotation-list.tsx
  - RAF-batched position measurement (getBoundingClientRect per annotated node)
  - Absolutely positions annotation cards in margin
        ↓
annotation-card.tsx (per annotation)
  - shows AI question/suggestion
  - action buttons depend on annotation type
        ↓
User action:
  "Create Issue"  → dispatches /create-issue to PilotSpaceAgent
  "Ask AI"        → sends to chat panel with annotation context
  "Dismiss"       → PATCH /api/v1/ai/annotations/{id}/dismiss
  "Resolve"       → annotation.resolved = true, mark removed
```

---

## Components

### `MarginAnnotationAutoTriggerExtension.ts` — Detection Plugin

**Responsibility**: Monitors typing activity and triggers annotation generation when conditions are met.

**Trigger conditions**:
1. User stops typing for 2000ms (debounced)
2. Current block has ≥50 characters (noise filter)
3. Block type is `paragraph` or `heading` (not code, list item, or media)
4. No ongoing annotation request for this block (dedup guard)

**Context collection** (3-block window):
```typescript
const context = [
  prevBlock?.textContent,   // Block before cursor
  currentBlock.textContent, // Block with cursor
  nextBlock?.textContent,   // Block after cursor
].filter(Boolean).join('\n\n');
```

The 3-block window gives the AI enough context to understand whether ambiguity is local ("what does 'it' refer to?") or structural ("this heading has no supporting paragraphs").

**Guard against rapid re-triggering**:
- Tracks `lastTriggeredBlockId + lastTriggeredContent`
- Only triggers if block content has changed since last trigger
- Prevents annotation storm while user is editing a single block

---

### `MarginAnnotationExtension.ts` — Mark Renderer

**Responsibility**: Applies ProseMirror marks to annotated text ranges, enabling visual highlighting.

**Mark application**:
```typescript
editor.commands.setMark('annotationMark', {
  annotationId: annotation.id,
  color: annotation.color,   // CSS variable name (e.g., 'annotation-amber')
  type: annotation.type,     // 'ambiguity' | 'action_item' | 'question' | 'suggestion'
});
```

**Visual output**: The AnnotationMark renders as a `<mark>` element with a colored underline (not background highlight). Different annotation types use different colors:

| Type | Color | Meaning |
|------|-------|---------|
| `ambiguity` | Amber | Unclear reference or missing context |
| `action_item` | Blue | Detected task or commitment |
| `question` | Purple | Unanswered question in text |
| `suggestion` | Green | Improvement opportunity |

**Mark removal**: When user dismisses or resolves an annotation, `removeMark('annotationMark', { annotationId })` removes only the specific mark by ID, not all annotation marks in the document.

---

### `AnnotationMark.ts` — ProseMirror Mark Type

**Responsibility**: Defines the TipTap Mark schema for annotation highlights.

```typescript
export const AnnotationMark = Mark.create({
  name: 'annotationMark',
  keepOnSplit: false,    // Don't carry mark when user presses Enter
  exitable: true,        // Cursor can exit mark at boundaries
  addAttributes() {
    return {
      annotationId: { default: null },
      color: { default: 'annotation-amber' },
      type: { default: 'ambiguity' },
    };
  },
  renderHTML({ HTMLAttributes }) {
    return ['mark', { 'data-annotation-id': HTMLAttributes.annotationId, ... }, 0];
  },
});
```

**`keepOnSplit: false`**: If the user presses Enter in the middle of an annotated sentence, the new paragraph does NOT inherit the annotation mark. Annotations belong to the original text block, not extended content.

---

### `margin-annotation-list.tsx` — Position Management

**Responsibility**: Maintains the mapping from annotation marks → margin card positions, using RAF-batched DOM measurements.

**Positioning strategy**:
```typescript
// On scroll or content change:
useEffect(() => {
  const updatePositions = () => {
    const positions: Record<string, number> = {};

    annotations.forEach((annotation) => {
      const markEl = document.querySelector(
        `[data-annotation-id="${annotation.id}"]`
      );
      if (markEl) {
        const rect = markEl.getBoundingClientRect();
        positions[annotation.id] = rect.top + window.scrollY;
      }
    });

    setCardPositions(positions);
  };

  // RAF batching: only 1 update per frame, not per scroll event
  const rafId = requestAnimationFrame(updatePositions);
  return () => cancelAnimationFrame(rafId);
}, [annotations, scrollY, contentVersion]);
```

**Collision avoidance**: When two annotation cards would overlap (their vertical positions differ by < 80px), the later card is pushed down by `Math.max(0, prevBottom - top + 8)`. This ensures readability at the cost of slight vertical offset from the annotated text.

**Performance**: Without RAF batching, scroll events fire at 60+ Hz and each would trigger `getBoundingClientRect()` for every annotation. RAF batching ensures position updates happen once per animation frame.

---

### `annotation-card.tsx` — Margin Card Component

**Responsibility**: Renders a single annotation as a floating card in the margin.

**Card structure**:
```
┌─────────────────────────────────────────┐
│ ≈ annotation-card                       │
│ ┌─────────────────────────────────────┐ │
│ │ [icon] What does "the system" refer │ │
│ │        to here?                     │ │
│ └─────────────────────────────────────┘ │
│ [Create Issue]  [Ask AI]  [Dismiss]    │
└─────────────────────────────────────────┘
```

**Action handlers by annotation type**:

| Annotation Type | Available Actions |
|-----------------|-------------------|
| `ambiguity` | "Ask AI for context", "Dismiss" |
| `action_item` | "Create Issue", "Ask AI", "Dismiss" |
| `question` | "Create Issue", "Ask AI", "Dismiss" |
| `suggestion` | "Apply Suggestion", "Ask AI", "Dismiss" |

**"Create Issue" flow**:
```typescript
const handleCreateIssue = () => {
  chatStore.sendMessage(`/create-issue from annotation: "${annotation.text}"`);
  chatStore.open();
};
```
This dispatches a slash command to PilotSpaceAgent with the annotated text pre-filled, routing through the standard approval workflow (DD-003).

**"Ask AI" flow**:
```typescript
const handleAskAI = () => {
  chatStore.sendMessage(annotation.question);
  chatStore.open();
};
```
Sends the annotation's question text directly to the chat, providing full note context for the AI response.

**"Apply Suggestion" flow** (only for `suggestion` type):
```typescript
const handleApplySuggestion = () => {
  editor.commands.setTextSelection(annotation.range);
  chatStore.sendMessage(`/improve-writing apply: ${annotation.suggestion}`);
};
```
Selects the annotated text range and triggers the `improve-writing` skill with the AI's specific suggestion.

---

### `annotation-detail-popover.tsx` — Expanded View

**Responsibility**: Shows full annotation context when user hovers/clicks the annotation mark in text.

- Appears as a floating popover attached to the mark element
- Shows: full annotation text, confidence score (internal), source block text
- Actions: same as card (Create Issue / Ask AI / Dismiss)
- Linked to `annotation-card.tsx` — clicking popover action also updates card state

---

## AnnotationStore (MobX)

**State shape**:
```typescript
interface AnnotationStore {
  annotations: Map<string, Annotation>;     // Keyed by annotationId
  loadingNoteId: string | null;             // Which note is being analyzed
  cache: Map<string, CachedAnnotation[]>;   // noteId → annotations (5-min TTL)
}

interface Annotation {
  id: string;
  noteId: string;
  blockId: string;
  textRange: { from: number; to: number };
  type: 'ambiguity' | 'action_item' | 'question' | 'suggestion';
  question: string;       // The AI's question or suggestion
  confidence: number;
  color: string;
  state: AnnotationState; // 'detected' | 'loading' | 'shown' | 'dismissed' | 'resolved'
  suggestion?: string;    // Only for 'suggestion' type
}
```

**SSE streaming handling**:
```typescript
// runInAction required for MobX in async callbacks
source.addEventListener('annotation', (event) => {
  const annotation = JSON.parse(event.data);
  runInAction(() => {
    this.annotations.set(annotation.id, { ...annotation, state: 'shown' });
  });
});
```

Without `runInAction()`, MobX in strict mode throws because observable mutations outside actions are forbidden. SSE event callbacks are async browser callbacks, not MobX actions.

**5-minute cache**:
```typescript
const cached = this.cache.get(noteId);
if (cached && Date.now() - cached.timestamp < 5 * 60 * 1000) {
  // Restore from cache without API call
  runInAction(() => {
    cached.annotations.forEach(a => this.annotations.set(a.id, a));
  });
  return;
}
```

Prevents re-analysis when user returns to the same note within 5 minutes. Cache is invalidated when note content changes by more than 20% (Levenshtein ratio check).

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `POST /api/v1/ai/annotations` | SSE | Generate annotations for a note block |
| `GET /api/v1/ai/annotations/{noteId}` | REST | Fetch persisted annotations for a note |
| `PATCH /api/v1/ai/annotations/{id}/dismiss` | REST | Dismiss an annotation |
| `PATCH /api/v1/ai/annotations/{id}/resolve` | REST | Mark annotation as resolved |

**SSE request body**:
```json
{
  "workspace_id": "...",
  "note_id": "...",
  "block_id": "...",
  "context": "3-block surrounding text",
  "existing_annotation_ids": ["..."]  // Prevents re-generating seen annotations
}
```

---

## 5-State Machine

```
detected ──→ loading ──→ shown
                           │
                    ┌──────┴──────┐
                    ↓             ↓
                dismissed       resolved
```

| State | Meaning | UI |
|-------|---------|-----|
| `detected` | Backend triggered, request in flight | No UI yet |
| `loading` | SSE stream connected, tokens arriving | Card with skeleton |
| `shown` | Full annotation visible in margin | Card with actions |
| `dismissed` | User dismissed without acting | Card fades out, mark removed |
| `resolved` | User acted (created issue/applied suggestion) | Card fades out, mark removed with checkmark |

---

## Implicit Features

| Feature | Mechanism | File |
|---------|-----------|------|
| RAF-batched position updates | `requestAnimationFrame()` wraps `getBoundingClientRect()` | `margin-annotation-list.tsx` |
| Collision avoidance | Card pushed down when overlap < 80px | `margin-annotation-list.tsx` |
| Immutable state updates | New array/object refs for MobX reactivity | `AnnotationStore.ts` |
| `runInAction()` in SSE callbacks | Required for MobX strict mode async | `AnnotationStore.ts` |
| 5-minute cache per note | Prevents re-analysis on same content | `AnnotationStore.ts` |
| 50-char minimum trigger | Filters noise (short blocks produce low-quality annotations) | `MarginAnnotationAutoTriggerExtension.ts` |
| `keepOnSplit: false` mark | Annotations don't extend to new paragraphs | `AnnotationMark.ts` |
| Type-based color coding | Amber/Blue/Purple/Green by annotation type | `MarginAnnotationExtension.ts` |
| Collision with dismissal state | Dismissed annotations cleared from AnnotationStore | `annotation-card.tsx` |
| Existing annotation dedup | `existing_annotation_ids` in request prevents re-generation | `AnnotationStore.ts` |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| 2000ms debounce (vs 500ms for ghost text) | Annotations are higher-cost analysis. 2s ensures user has finished their thought. |
| Margin placement (not inline) | Inline suggestions break writing flow. Margin cards are ambient — visible but non-blocking. |
| 3-block context window | Single block is often insufficient for ambiguity detection. 3 blocks cover most structural context. |
| RAF batching for positions | getBoundingClientRect() on scroll fires 60+ times/second. RAF = 1 update/frame. |
| SSE for generation (not polling) | Annotation streaming shows first card while others generate. Improves perceived performance. |
| 5-minute cache | Re-analysis of unchanged content wastes tokens. Content-change invalidation handles edits. |
| `runInAction()` in SSE | MobX strict mode requires all mutations in actions. SSE callbacks are async browser events. |

---

## Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `editor/extensions/MarginAnnotationAutoTriggerExtension.ts` | ~200 | 2000ms debounce, 3-block context, trigger conditions |
| `editor/extensions/MarginAnnotationExtension.ts` | ~180 | Mark application by annotationId, color, type |
| `editor/extensions/AnnotationMark.ts` | ~100 | ProseMirror mark schema, keepOnSplit: false |
| `components/margin-annotation-list.tsx` | ~250 | RAF-batched positioning, collision avoidance |
| `components/annotation-card.tsx` | ~200 | Margin card UI, action dispatch to PilotSpaceAgent |
| `components/annotation-detail-popover.tsx` | ~150 | Hover popover on annotated text |
| `stores/AnnotationStore.ts` | ~300 | MobX state, SSE streaming, 5-min cache |

# Margin Annotations Integration Guide

## Overview

This directory contains the UI components for the Margin Annotations feature (US6, T165-T177). The feature displays AI-powered annotations in the right margin of the note editor, linked to specific content blocks.

## Components

### AnnotationCard (`annotation-card.tsx`)
Individual annotation display with:
- Type-specific icons (Lightbulb, AlertTriangle, HelpCircle, Sparkles, Link2)
- Type-specific colors (blue, amber, purple, green, gray)
- Confidence indicator (0-100%)
- Selection state highlighting
- Hover effects

### MarginAnnotationList (`margin-annotation-list.tsx`)
Container component that:
- Positions annotations based on block locations
- Groups annotations by block
- Handles selection via store
- Provides empty state

### AnnotationDetailPopover (`annotation-detail-popover.tsx`)
Detailed view with:
- Full annotation content
- Suggested text replacement preview
- References list with external links
- Apply and Dismiss actions

## Store Integration

The feature uses `MarginAnnotationStore` from `@/stores/ai/MarginAnnotationStore`:

```typescript
const { ai } = useStores();
const { marginAnnotation } = ai;

// Generate annotations via SSE
await marginAnnotation.generateAnnotations(noteId, blocks);

// Get annotations by block
const annotationsByBlock = marginAnnotation.getAnnotationsByBlock(noteId);

// Select annotation
marginAnnotation.selectAnnotation(annotationId);

// Dismiss annotation
marginAnnotation.dismissAnnotation(annotationId);
```

## TipTap Extension Integration

### In your editor setup:

```typescript
import { MarginAnnotationExtension } from '@/components/editor/extensions/margin-annotation-extension';
import { createAnnotationPositioningPlugin } from '@/components/editor/plugins/annotation-positioning';
import { useStores } from '@/stores/RootStore';

function MyEditor() {
  const { ai } = useStores();
  const [blockPositions, setBlockPositions] = useState<BlockPosition[]>([]);

  const editor = useEditor({
    extensions: [
      // ... other extensions
      MarginAnnotationExtension.configure({
        enabled: true,
        annotationStore: ai.marginAnnotation,
      }),
    ],
    editorProps: {
      plugins: [
        createAnnotationPositioningPlugin(setBlockPositions),
      ],
    },
  });

  return (
    <div className="flex">
      <div className="flex-1">
        <EditorContent editor={editor} />
      </div>
      <div className="w-72">
        <MarginAnnotationList
          noteId={noteId}
          blockPositions={blockPositions}
        />
      </div>
    </div>
  );
}
```

## SSE Streaming

Annotations are generated via Server-Sent Events:

```typescript
// Backend endpoint: POST /api/v1/ai/notes/{noteId}/annotations
// Events:
// - event: annotation, data: { id, blockId, type, title, content, ... }
// - event: complete
// - event: error
```

The store handles SSE automatically via `SSEClient`.

## Annotation Types

- **suggestion**: Actionable improvement (light bulb icon, blue)
- **warning**: Potential issue (alert icon, amber)
- **question**: Needs clarification (question mark icon, purple)
- **insight**: Background context (sparkles icon, green)
- **reference**: Related resources (link icon, gray)

## Accessibility

All components follow WCAG 2.2 AA standards:
- Semantic HTML with proper ARIA labels
- Keyboard navigation support
- Focus indicators
- Screen reader support
- Color contrast compliance

## Testing

Run tests with:

```bash
pnpm test src/stores/ai/__tests__/margin-annotation-store.test.ts
pnpm test src/features/notes/components/__tests__/margin-annotation-list.test.tsx
```

## CSS Classes

Key classes for styling:
- `.margin-annotation-indicator` - In-editor block indicators
- `.margin-annotation-list` - Sidebar container
- Type-specific colors via `typeColors` map in `annotation-card.tsx`

## Performance Considerations

- Position updates are batched with `requestAnimationFrame`
- Annotations are grouped by block for efficient rendering
- MobX observers ensure minimal re-renders
- Virtual scrolling recommended for 100+ annotations

## Future Enhancements (Post-MVP)

- Batch operations (dismiss all, apply all)
- Annotation filters (by type, confidence)
- Annotation history and undo
- Collaborative annotation discussions
- Export annotations to markdown

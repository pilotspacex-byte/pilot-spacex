/**
 * Margin Annotation Extension - TipTap extension for AI annotations
 * T165: Displays AI annotations in the right margin linked to note blocks
 *
 * Features:
 * - Inline indicators for annotated blocks
 * - Integration with MarginAnnotationStore
 * - Click handlers for annotation selection
 */
import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import type { Node as PMNode } from '@tiptap/pm/model';
import type { MarginAnnotationStore, NoteAnnotation } from '@/stores/ai/MarginAnnotationStore';

export interface MarginAnnotationOptions {
  enabled: boolean;
  annotationStore: MarginAnnotationStore;
}

export const marginAnnotationPluginKey = new PluginKey('marginAnnotation');

/**
 * TipTap extension for margin annotations.
 * Creates decoration indicators for blocks with annotations.
 */
export const MarginAnnotationExtension = Extension.create<MarginAnnotationOptions>({
  name: 'marginAnnotation',

  addOptions() {
    return {
      enabled: true,
      annotationStore: null!,
    };
  },

  addProseMirrorPlugins() {
    const { enabled, annotationStore } = this.options;

    if (!enabled || !annotationStore) return [];

    return [
      new Plugin({
        key: marginAnnotationPluginKey,
        state: {
          init() {
            return DecorationSet.empty;
          },
          apply(tr, oldSet, _oldState, newState) {
            // Update decorations on document changes or annotation updates
            const meta = tr.getMeta(marginAnnotationPluginKey);

            if (meta?.forceUpdate) {
              return buildDecorations(newState.doc, annotationStore);
            }

            // If document changed, rebuild decorations
            if (tr.docChanged) {
              return buildDecorations(newState.doc, annotationStore);
            }

            // Map old decorations if document structure changed
            return oldSet.map(tr.mapping, tr.doc);
          },
        },
        props: {
          decorations(state) {
            return this.getState(state);
          },
          handleClickOn(_view, _pos, _node, _nodePos, event) {
            const target = event.target as HTMLElement;

            // Check if clicked on annotation indicator
            if (target.classList.contains('margin-annotation-indicator')) {
              const annotationId = target.dataset.annotationId;
              if (annotationId) {
                annotationStore.selectAnnotation(annotationId);
                event.preventDefault();
                return true;
              }
            }
            return false;
          },
        },
      }),
    ];
  },

  addCommands() {
    // Return type needs to match TipTap's command structure
    // Using any here because TipTap's types are complex
    return {
      /**
       * Force rebuild decorations (call after store updates)
       */
      updateMarginAnnotations:
        () =>
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        ({ tr, dispatch }: any) => {
          if (dispatch) {
            tr.setMeta(marginAnnotationPluginKey, { forceUpdate: true });
            dispatch(tr);
          }
          return true;
        },
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any;
  },
});

/**
 * Build decoration widgets for blocks with annotations.
 * Creates small indicators in the editor margin.
 */
function buildDecorations(doc: PMNode, store: MarginAnnotationStore): DecorationSet {
  const decorations: Decoration[] = [];
  const annotations = store.getAnnotationsForDoc();

  if (!annotations || annotations.length === 0) {
    return DecorationSet.empty;
  }

  // Group annotations by block ID for efficient lookup
  const annotationsByBlock = new Map<string, NoteAnnotation[]>();
  annotations.forEach((annotation) => {
    const existing = annotationsByBlock.get(annotation.blockId) || [];
    annotationsByBlock.set(annotation.blockId, [...existing, annotation]);
  });

  // Traverse document to find blocks with annotations
  doc.descendants((node: PMNode, pos: number) => {
    if (node.isBlock && node.attrs.blockId) {
      const blockAnnotations = annotationsByBlock.get(node.attrs.blockId);

      if (blockAnnotations && blockAnnotations.length > 0) {
        // Create indicator widget at block start
        const widget = Decoration.widget(pos + 1, () => createIndicatorWidget(blockAnnotations), {
          side: 1,
          key: `annotation-${node.attrs.blockId}`,
        });
        decorations.push(widget);
      }
    }
  });

  return DecorationSet.create(doc, decorations);
}

/**
 * Create DOM element for annotation indicator.
 * Shows count badge and type-specific icon.
 */
function createIndicatorWidget(annotations: NoteAnnotation[]): HTMLElement {
  const container = document.createElement('span');
  container.className = 'margin-annotation-indicator';
  container.setAttribute('data-annotation-id', annotations[0]?.id || '');
  container.setAttribute('aria-label', `${annotations.length} annotation(s)`);
  container.style.cssText = `
    position: absolute;
    right: -28px;
    top: 4px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: var(--ai-muted, hsl(210 40% 55% / 0.1));
    border: 1px solid var(--ai-border, hsl(210 40% 55% / 0.2));
    cursor: pointer;
    transition: all 150ms ease-out;
    z-index: 1;
  `;

  // Count badge
  const badge = document.createElement('span');
  badge.className = 'annotation-count';
  badge.textContent = annotations.length.toString();
  badge.style.cssText = `
    font-size: 10px;
    font-weight: 600;
    color: var(--ai, hsl(210 40% 55%));
  `;
  container.appendChild(badge);

  // Hover effect
  container.addEventListener('mouseenter', () => {
    container.style.background = 'var(--ai-muted, hsl(210 40% 55% / 0.2))';
    container.style.borderColor = 'var(--ai, hsl(210 40% 55%))';
  });

  container.addEventListener('mouseleave', () => {
    container.style.background = 'var(--ai-muted, hsl(210 40% 55% / 0.1))';
    container.style.borderColor = 'var(--ai-border, hsl(210 40% 55% / 0.2))';
  });

  return container;
}

/**
 * Find document position for a block ID.
 * Returns null if block not found.
 */
export function findBlockPosition(doc: PMNode, blockId: string): number | null {
  let position: number | null = null;

  doc.descendants((node: PMNode, pos: number) => {
    if (position !== null) return false;
    if (node.isBlock && node.attrs.blockId === blockId) {
      position = pos;
      return false;
    }
    return true;
  });

  return position;
}

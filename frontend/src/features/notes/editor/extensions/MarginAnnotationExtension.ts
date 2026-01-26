/**
 * MarginAnnotationExtension - Displays annotation indicators in the left gutter
 *
 * Features:
 * - Adds data-annotation-count attribute to annotated blocks
 * - Visual indicator (colored dot) in left gutter
 * - Click to scroll margin panel to annotation
 * - Color coding: blue=suggestion, yellow=warning, purple=issue_candidate
 */
import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import type { Node as ProseMirrorNode } from '@tiptap/pm/model';
import type { AnnotationType } from '@/types';

/**
 * Annotation data for a single block
 */
export interface BlockAnnotationData {
  blockId: string;
  count: number;
  types: AnnotationType[];
}

export interface MarginAnnotationOptions {
  /** Annotations map: blockId -> annotation data */
  annotations: Map<string, BlockAnnotationData>;
  /** Callback when annotation indicator is clicked */
  onClick?: (blockId: string) => void;
  /** CSS class for the indicator container */
  indicatorClass: string;
}

interface MarginAnnotationPluginState {
  annotations: Map<string, BlockAnnotationData>;
  decorations: DecorationSet;
}

const MARGIN_ANNOTATION_PLUGIN_KEY = new PluginKey<MarginAnnotationPluginState>('marginAnnotation');

/**
 * Color mapping for annotation types
 */
const ANNOTATION_COLORS: Record<AnnotationType, string> = {
  suggestion: 'rgb(59, 130, 246)', // blue-500
  warning: 'rgb(234, 179, 8)', // yellow-500
  issue_candidate: 'rgb(168, 85, 247)', // purple-500
  info: 'rgb(107, 114, 128)', // gray-500
  question: 'rgb(147, 51, 234)', // purple-600
  insight: 'rgb(34, 197, 94)', // green-500
  reference: 'rgb(107, 114, 128)', // gray-500
};

/**
 * Creates an annotation indicator widget for the left gutter
 */
function createIndicatorWidget(
  data: BlockAnnotationData,
  onClick?: (blockId: string) => void,
  indicatorClass?: string
): HTMLElement {
  const container = document.createElement('div');
  container.className = `margin-annotation-indicator ${indicatorClass ?? ''}`;
  container.setAttribute('data-block-id', data.blockId);
  container.setAttribute('data-annotation-count', String(data.count));
  container.setAttribute('aria-label', `${data.count} annotation${data.count > 1 ? 's' : ''}`);
  container.setAttribute('role', 'button');
  container.setAttribute('tabindex', '0');

  // Determine primary color based on annotation types
  const primaryType = data.types[0] ?? 'suggestion';
  const primaryColor = ANNOTATION_COLORS[primaryType];

  // Create the dot indicator
  const dot = document.createElement('span');
  dot.className = 'margin-annotation-dot';
  dot.style.cssText = `
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: ${primaryColor};
    cursor: pointer;
    transition: transform 0.15s ease;
  `;

  // Add count badge if more than 1
  if (data.count > 1) {
    const badge = document.createElement('span');
    badge.className = 'margin-annotation-count';
    badge.textContent = String(data.count);
    badge.style.cssText = `
      position: absolute;
      top: -4px;
      right: -4px;
      font-size: 10px;
      min-width: 14px;
      height: 14px;
      line-height: 14px;
      text-align: center;
      background-color: ${primaryColor};
      color: white;
      border-radius: 7px;
      font-weight: 600;
    `;
    container.appendChild(badge);
  }

  container.appendChild(dot);

  // Container styles
  container.style.cssText = `
    position: absolute;
    left: -24px;
    top: 50%;
    transform: translateY(-50%);
    display: flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
  `;

  // Click handler
  if (onClick) {
    container.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      onClick(data.blockId);
    });

    container.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onClick(data.blockId);
      }
    });
  }

  // Hover effect
  container.addEventListener('mouseenter', () => {
    dot.style.transform = 'scale(1.2)';
  });
  container.addEventListener('mouseleave', () => {
    dot.style.transform = 'scale(1)';
  });

  return container;
}

/**
 * MarginAnnotationExtension adds visual indicators to blocks with annotations
 *
 * @example
 * ```tsx
 * import { MarginAnnotationExtension } from './extensions/MarginAnnotationExtension';
 *
 * const annotations = new Map([
 *   ['block-1', { blockId: 'block-1', count: 2, types: ['suggestion', 'warning'] }],
 * ]);
 *
 * const editor = new Editor({
 *   extensions: [
 *     MarginAnnotationExtension.configure({
 *       annotations,
 *       onClick: (blockId) => {
 *         // Scroll to annotation in margin panel
 *       },
 *     }),
 *   ],
 * });
 * ```
 */
export const MarginAnnotationExtension = Extension.create<MarginAnnotationOptions>({
  name: 'marginAnnotation',

  addOptions() {
    return {
      annotations: new Map(),
      onClick: undefined,
      indicatorClass: '',
    };
  },

  // eslint-disable-next-line @typescript-eslint/ban-ts-comment
  // @ts-ignore TipTap's RawCommands type requires specific signatures
  addCommands() {
    return {
      /**
       * Update annotations data
       */
      setAnnotations:
        (annotations: Map<string, BlockAnnotationData>) =>
        ({ editor }) => {
          this.options.annotations = annotations;

          // Trigger a state update to refresh decorations
          editor.view.dispatch(
            editor.state.tr.setMeta(MARGIN_ANNOTATION_PLUGIN_KEY, { annotations })
          );

          return true;
        },

      /**
       * Update a single block's annotations
       */
      updateBlockAnnotation:
        (blockId: string, data: BlockAnnotationData | null) =>
        ({ editor }) => {
          if (data) {
            this.options.annotations.set(blockId, data);
          } else {
            this.options.annotations.delete(blockId);
          }

          editor.view.dispatch(
            editor.state.tr.setMeta(MARGIN_ANNOTATION_PLUGIN_KEY, {
              annotations: this.options.annotations,
            })
          );

          return true;
        },

      /**
       * Clear all annotations
       */
      clearAnnotations:
        () =>
        ({ editor }) => {
          this.options.annotations.clear();

          editor.view.dispatch(
            editor.state.tr.setMeta(MARGIN_ANNOTATION_PLUGIN_KEY, {
              annotations: new Map(),
            })
          );

          return true;
        },
    };
  },

  addProseMirrorPlugins() {
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    const extension = this;

    return [
      new Plugin<MarginAnnotationPluginState>({
        key: MARGIN_ANNOTATION_PLUGIN_KEY,

        state: {
          init(_, state) {
            return {
              annotations: extension.options.annotations,
              decorations: buildDecorations(
                state.doc,
                extension.options.annotations,
                extension.options.onClick,
                extension.options.indicatorClass
              ),
            };
          },

          apply(tr, value, _oldState, newState) {
            const meta = tr.getMeta(MARGIN_ANNOTATION_PLUGIN_KEY);

            if (meta?.annotations) {
              return {
                annotations: meta.annotations,
                decorations: buildDecorations(
                  newState.doc,
                  meta.annotations,
                  extension.options.onClick,
                  extension.options.indicatorClass
                ),
              };
            }

            // Rebuild if document changed
            if (tr.docChanged) {
              return {
                annotations: value.annotations,
                decorations: buildDecorations(
                  newState.doc,
                  value.annotations,
                  extension.options.onClick,
                  extension.options.indicatorClass
                ),
              };
            }

            return value;
          },
        },

        props: {
          decorations(state) {
            return this.getState(state)?.decorations ?? DecorationSet.empty;
          },
        },
      }),
    ];
  },
});

/**
 * Build decorations for all annotated blocks
 */
function buildDecorations(
  doc: ProseMirrorNode,
  annotations: Map<string, BlockAnnotationData>,
  onClick?: (blockId: string) => void,
  indicatorClass?: string
): DecorationSet {
  if (annotations.size === 0) {
    return DecorationSet.empty;
  }

  const decorations: Decoration[] = [];

  doc.descendants((node, pos) => {
    // Only process block nodes with IDs
    const blockId = node.attrs?.blockId as string | undefined;
    if (!blockId || !node.isBlock) {
      return true;
    }

    const annotationData = annotations.get(blockId);
    if (!annotationData) {
      return true;
    }

    // Add node decoration with annotation count
    decorations.push(
      Decoration.node(pos, pos + node.nodeSize, {
        'data-annotation-count': String(annotationData.count),
        'data-annotation-types': annotationData.types.join(','),
        class: 'has-annotations',
      })
    );

    // Add widget decoration for the indicator
    decorations.push(
      Decoration.widget(pos, () => createIndicatorWidget(annotationData, onClick, indicatorClass), {
        side: -1,
        key: `annotation-indicator-${blockId}`,
      })
    );

    return true;
  });

  return DecorationSet.create(doc, decorations);
}

// Type augmentation for TipTap commands
declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    marginAnnotation: {
      setAnnotations: (annotations: Map<string, BlockAnnotationData>) => ReturnType;
      updateBlockAnnotation: (blockId: string, data: BlockAnnotationData | null) => ReturnType;
      clearAnnotations: () => ReturnType;
    };
  }
}

/**
 * CSS styles for margin annotations (add to your global stylesheet)
 */
export const marginAnnotationStyles = `
  .has-annotations {
    position: relative;
  }

  .margin-annotation-indicator {
    z-index: 10;
  }

  .margin-annotation-indicator:focus {
    outline: 2px solid var(--ring, #3b82f6);
    outline-offset: 2px;
    border-radius: 4px;
  }

  .margin-annotation-dot {
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  }

  .margin-annotation-count {
    font-family: var(--font-mono, monospace);
  }
`;

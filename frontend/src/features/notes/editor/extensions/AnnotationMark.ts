/**
 * AnnotationMark - Mark extension for highlighting annotated text
 * Visually indicates which text has AI annotations in the margin
 */
import { Mark, mergeAttributes, type CommandProps } from '@tiptap/core';
import type { Mark as ProseMirrorMark } from '@tiptap/pm/model';
import type { AnnotationType } from '@/types';

export interface AnnotationMarkOptions {
  /** HTML tag to use for annotations */
  HTMLAttributes: Record<string, unknown>;
  /** CSS class for annotation highlighting */
  className: string;
}

/**
 * AnnotationMark highlights text that has associated annotations
 *
 * Features:
 * - Subtle background highlight on annotated text
 * - Stores annotation ID for linking with margin panel
 * - Click handler to focus annotation in sidebar
 * - Multiple overlapping annotations supported
 */
export const AnnotationMark = Mark.create<AnnotationMarkOptions>({
  name: 'annotation',

  addOptions() {
    return {
      HTMLAttributes: {},
      className: 'annotation-highlight',
    };
  },

  addAttributes() {
    return {
      annotationId: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-annotation-id'),
        renderHTML: (attributes) => {
          if (!attributes.annotationId) return {};
          return { 'data-annotation-id': attributes.annotationId };
        },
      },
      annotationType: {
        default: 'suggestion' as AnnotationType,
        parseHTML: (element) =>
          (element.getAttribute('data-annotation-type') as AnnotationType) ?? 'suggestion',
        renderHTML: (attributes) => {
          return { 'data-annotation-type': attributes.annotationType };
        },
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'span[data-annotation-id]',
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'span',
      mergeAttributes(this.options.HTMLAttributes, HTMLAttributes, {
        class: this.options.className,
        style: `
          background-color: var(--annotation-bg, rgba(var(--ai-rgb), 0.1));
          border-bottom: 2px solid var(--annotation-border, rgba(var(--ai-rgb), 0.3));
          cursor: pointer;
        `,
      }),
      0,
    ];
  },

  // eslint-disable-next-line @typescript-eslint/ban-ts-comment
  // @ts-ignore TipTap's RawCommands type requires specific signatures
  addCommands() {
    return {
      /**
       * Set annotation mark on selected text
       */
      setAnnotation:
        (annotationId: string, type: AnnotationType = 'suggestion') =>
        ({ commands }: CommandProps) => {
          return commands.setMark(this.name, { annotationId, annotationType: type });
        },

      /**
       * Remove annotation mark
       */
      removeAnnotation:
        (annotationId: string) =>
        ({ tr, state, dispatch }: CommandProps) => {
          let found = false;
          const extensionName = this.name;

          state.doc.descendants((node, pos) => {
            if (node.isText) {
              const matchingMarks: ProseMirrorMark[] = [];
              node.marks.forEach((mark) => {
                if (mark.type.name === extensionName && mark.attrs.annotationId === annotationId) {
                  matchingMarks.push(mark);
                }
              });

              if (matchingMarks.length > 0) {
                found = true;
                if (dispatch) {
                  matchingMarks.forEach((mark) => {
                    tr.removeMark(pos, pos + node.nodeSize, mark);
                  });
                }
              }
            }
            return true;
          });

          if (found && dispatch) {
            dispatch(tr);
          }

          return found;
        },

      /**
       * Toggle annotation mark on selection
       */
      toggleAnnotation:
        (annotationId: string, type: AnnotationType = 'suggestion') =>
        ({ commands }: CommandProps) => {
          return commands.toggleMark(this.name, { annotationId, annotationType: type });
        },

      /**
       * Clear all annotations
       */
      clearAllAnnotations:
        () =>
        ({ commands }: CommandProps) => {
          return commands.unsetMark(this.name);
        },
    };
  },
});

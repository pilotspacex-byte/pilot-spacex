/**
 * FileCardExtension — TipTap atom block node for uploaded file cards.
 *
 * Renders uploaded files as styled interactive cards inside the note editor.
 * Supports three status states: uploading (progress bar), ready (metadata),
 * and error (retry button). NodeView is delegated to FileCardNodeView (plain,
 * non-observer) which bridges to FileCardView (observer) via FileCardContext.
 *
 * Markdown serialization: ready nodes emit `[filename](artifact://uuid)`.
 * Uploading nodes (artifactId: null) emit empty string — omitted from markdown.
 *
 * ## Registration
 * Must be registered in Group 3 of createEditorExtensions.ts, BEFORE BlockIdExtension.
 *
 * @module file-card/FileCardExtension
 */
import { Node, mergeAttributes } from '@tiptap/core';
import { ReactNodeViewRenderer } from '@tiptap/react';
import { FileCardNodeView } from './FileCardNodeView';

export const FileCardExtension = Node.create({
  name: 'fileCard',
  group: 'block',
  atom: true,
  draggable: true,

  // NOTE: Do NOT add addExtensions() with StarterKit here.
  // ProseMirror's keyed plugins (history$) throw RangeError on duplicates
  // when the parent editor already registers StarterKit via createEditorExtensions.
  // Tests should explicitly include StarterKit + Markdown in their own editor setup.

  addAttributes() {
    return {
      artifactId: {
        default: null,
        parseHTML: (el) => el.getAttribute('data-artifact-id') || null,
        renderHTML: (attrs) => ({ 'data-artifact-id': attrs.artifactId }),
      },
      filename: {
        default: '',
        parseHTML: (el) => el.getAttribute('data-filename') || '',
        renderHTML: (attrs) => ({ 'data-filename': attrs.filename }),
      },
      mimeType: {
        default: '',
        parseHTML: (el) => el.getAttribute('data-mime-type') || '',
        renderHTML: (attrs) => ({ 'data-mime-type': attrs.mimeType }),
      },
      sizeBytes: {
        default: 0,
        parseHTML: (el) => parseInt(el.getAttribute('data-size-bytes') || '0', 10),
        renderHTML: (attrs) => ({ 'data-size-bytes': String(attrs.sizeBytes) }),
      },
      status: {
        default: 'uploading',
        parseHTML: (el) => el.getAttribute('data-status') || 'ready',
        renderHTML: (attrs) => ({ 'data-status': attrs.status }),
      },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-file-card]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, { 'data-file-card': '', class: 'file-card' })];
  },

  addNodeView() {
    return ReactNodeViewRenderer(FileCardNodeView, {
      // Stop mouse events so ProseMirror's selectClickedLeaf doesn't fire.
      // Without this, ProseMirror dispatches a NodeSelection transaction which
      // triggers TipTap's ReactRenderer.flushSync inside React's lifecycle,
      // causing "flushSync was called from inside a lifecycle method" + RangeError.
      stopEvent: ({ event }) => {
        const t = event.type;
        return t === 'mousedown' || t === 'mouseup' || t === 'click';
      },
    });
  },

  addStorage() {
    return {
      markdown: {
        serialize(
          state: { write: (text: string) => void; closeBlock: (node: unknown) => void },
          node: { attrs: Record<string, unknown> }
        ) {
          const { artifactId, filename } = node.attrs as {
            artifactId: string | null;
            filename: string;
          };
          if (!artifactId) {
            // Stale uploading node — emit nothing, close the block cleanly
            state.closeBlock(node);
            return;
          }
          state.write(`[${filename}](artifact://${artifactId})`);
          state.closeBlock(node);
        },
        parse: {},
      },
    };
  },
});

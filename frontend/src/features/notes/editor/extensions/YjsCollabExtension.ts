/**
 * YjsCollabExtension — TipTap extension binding Yjs CRDT to ProseMirror.
 *
 * T-101: Minimal Yjs + TipTap binding POC (y-prosemirror, two-tab merge).
 * T-118: Full provider with auto-reconnect and error boundary.
 *
 * Spec: specs/016-note-collaboration/spec.md §M6a
 *
 * Architecture:
 *   TipTap Editor ↔ Y.Doc (XmlFragment "prosemirror") ↔ Provider
 *
 * This extension manages the Y.Doc and ProseMirror binding only.
 * Provider connection lifecycle is handled by YjsProvider (useYjsProvider hook).
 *
 * CRDT bundle size: ~40KB gzip (y-prosemirror + yjs). Acceptable per R-005 (<100KB).
 */
import { Extension } from '@tiptap/core';
import * as Y from 'yjs';
import { ySyncPlugin, yUndoPlugin, yCursorPlugin, undo, redo } from 'y-prosemirror';
import type { Awareness } from 'y-protocols/awareness';
import type { AnyExtension } from '@tiptap/core';

export interface YjsCollabOptions {
  /** The Yjs document. Must be created externally and passed in. */
  document: Y.Doc;
  /** Yjs Awareness instance for cursors and presence. */
  awareness: Awareness;
  /**
   * Name of the XmlFragment in the Y.Doc.
   * Defaults to 'prosemirror' (y-prosemirror convention).
   */
  field?: string;
}

/**
 * Creates a TipTap extension that binds Yjs CRDT to the ProseMirror editor.
 * Adds ySyncPlugin, yUndoPlugin, and yCursorPlugin.
 *
 * @example
 * ```ts
 * const ydoc = new Y.Doc();
 * const awareness = new Awareness(ydoc);
 * const collabExt = createYjsCollabExtension({ document: ydoc, awareness });
 * ```
 */
export function createYjsCollabExtension(options: YjsCollabOptions): AnyExtension {
  const { document: ydoc, awareness, field = 'prosemirror' } = options;
  const yXmlFragment = ydoc.getXmlFragment(field);

  return Extension.create<YjsCollabOptions>({
    name: 'yjsCollab',

    priority: 1000, // Run before ownership/other extensions see the document

    addProseMirrorPlugins() {
      return [ySyncPlugin(yXmlFragment), yCursorPlugin(awareness), yUndoPlugin()];
    },

    addKeyboardShortcuts() {
      return {
        'Mod-z': () => undo(this.editor.state),
        'Mod-y': () => redo(this.editor.state),
        'Mod-Shift-z': () => redo(this.editor.state),
      };
    },
  });
}

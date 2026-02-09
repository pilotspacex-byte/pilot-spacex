/**
 * BlockIdExtension - Adds unique IDs to all block-level nodes
 * Essential for annotation linking and virtualization
 */
import { Extension } from '@tiptap/core';
import { Plugin, PluginKey, type Transaction } from '@tiptap/pm/state';
import type { EditorView } from '@tiptap/pm/view';
import { type Node as ProseMirrorNode } from '@tiptap/pm/model';

export interface BlockIdOptions {
  /** Function to generate unique IDs */
  generateId: () => string;
  /** Attribute name for block IDs */
  attributeName: string;
  /** Node types to add IDs to (defaults to all block types) */
  types: string[] | null;
}

const BLOCK_ID_PLUGIN_KEY = new PluginKey('blockId');
const AI_EDIT_GUARD_KEY = new PluginKey('aiEditGuard');

/** Navigation keys that should NOT be blocked even in pending blocks. */
const NAV_KEYS = new Set([
  'ArrowUp',
  'ArrowDown',
  'ArrowLeft',
  'ArrowRight',
  'Home',
  'End',
  'PageUp',
  'PageDown',
  'Tab',
  'Escape',
  'Shift',
  'Control',
  'Alt',
  'Meta',
  'F1',
  'F2',
  'F3',
  'F4',
  'F5',
  'F6',
  'F7',
  'F8',
  'F9',
  'F10',
  'F11',
  'F12',
]);

/**
 * Check if the current selection anchor is inside a block
 * that has the `ai-block-pending-edit` CSS class (applied by highlightBlock).
 *
 * Uses DOM state — fast O(1) check via classList + closest().
 * Only user DOM events call this; programmatic editor.commands bypass it.
 */
export function isSelectionInPendingBlock(view: EditorView): boolean {
  try {
    const { from } = view.state.selection;
    const domPos = view.domAtPos(from);
    const node = domPos.node;
    const el = node instanceof Element ? node : node.parentElement;
    const blockEl = el?.closest('[data-block-id]');
    return blockEl?.classList.contains('ai-block-pending-edit') ?? false;
  } catch {
    return false;
  }
}

/**
 * Generates a unique block ID using crypto API with fallback
 */
function generateBlockId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for environments without crypto.randomUUID
  return `${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * BlockIdExtension ensures every block-level node has a unique ID
 * Used for:
 * - Linking annotations to specific blocks
 * - Virtualization (tracking visible blocks)
 * - Scroll sync between editor and annotation panel
 */
export const BlockIdExtension = Extension.create<BlockIdOptions>({
  name: 'blockId',

  addOptions() {
    return {
      generateId: generateBlockId,
      attributeName: 'blockId',
      types: null, // null means all block types
    };
  },

  addGlobalAttributes() {
    const types = this.options.types ?? [
      'paragraph',
      'heading',
      'codeBlock',
      'blockquote',
      'bulletList',
      'orderedList',
      'listItem',
      'taskList',
      'taskItem',
      'horizontalRule',
      'table',
      'tableRow',
      'tableCell',
      'tableHeader',
    ];

    return [
      {
        types,
        attributes: {
          [this.options.attributeName]: {
            default: null,
            parseHTML: (element) =>
              element.getAttribute('data-block-id') ??
              element.getAttribute(`data-${this.options.attributeName}`),
            renderHTML: (attributes) => {
              const id = attributes[this.options.attributeName];
              if (!id) return {};
              return { 'data-block-id': id };
            },
          },
        },
      },
    ];
  },

  addProseMirrorPlugins() {
    const { generateId, attributeName, types } = this.options;

    return [
      new Plugin({
        key: BLOCK_ID_PLUGIN_KEY,
        appendTransaction: (_transactions, _oldState, newState) => {
          const tr: Transaction = newState.tr;
          let modified = false;

          newState.doc.descendants((node, pos) => {
            // Skip if node should not have an ID
            if (types !== null && !types.includes(node.type.name)) {
              return true;
            }

            // Skip non-block nodes (text, inline marks, etc.)
            if (!node.isBlock) {
              return true;
            }

            // Add ID if missing
            const currentId = node.attrs[attributeName];
            if (!currentId) {
              const id = generateId();
              tr.setNodeMarkup(pos, undefined, {
                ...node.attrs,
                [attributeName]: id,
              });
              modified = true;
            }

            return true;
          });

          return modified ? tr : null;
        },
      }),
      // Guard plugin: block user edits on AI-pending blocks.
      // Only intercepts DOM events (typing, paste, drop, key).
      // Programmatic editor.commands (AI content updates) bypass DOM handlers.
      new Plugin({
        key: AI_EDIT_GUARD_KEY,
        props: {
          handleTextInput(view) {
            return isSelectionInPendingBlock(view);
          },
          handleKeyDown(view, event) {
            if (isSelectionInPendingBlock(view) && !NAV_KEYS.has(event.key)) {
              return true;
            }
            return false;
          },
          handlePaste(view) {
            return isSelectionInPendingBlock(view);
          },
          handleDrop(view) {
            return isSelectionInPendingBlock(view);
          },
        },
      }),
    ];
  },
});

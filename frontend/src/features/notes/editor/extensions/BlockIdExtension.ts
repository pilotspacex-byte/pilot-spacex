/**
 * BlockIdExtension - Adds unique IDs to all block-level nodes
 * Essential for annotation linking and virtualization
 */
import { Extension } from '@tiptap/core';
import { Plugin, PluginKey, type Transaction } from '@tiptap/pm/state';
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
 * Checks if a node is a block-level node
 */
function isBlockNode(node: ProseMirrorNode): boolean {
  return node.isBlock && !node.isTextblock;
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

            // Skip non-block nodes
            if (!isBlockNode(node) && node.type.name !== 'paragraph') {
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
    ];
  },
});

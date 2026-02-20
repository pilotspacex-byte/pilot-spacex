/**
 * PropertyBlockNode - Custom TipTap Node extension for inline issue properties.
 *
 * Renders as an atom node at document position 0. Non-deletable via
 * appendTransaction enforcement. Uses ReactNodeViewRenderer for the
 * PropertyBlockView component.
 *
 * Data flows through IssueNoteContext (React context), NOT through
 * TipTap node attributes, to avoid serialization overhead.
 */
import { Node } from '@tiptap/core';
import { ReactNodeViewRenderer } from '@tiptap/react';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { PropertyBlockView } from '@/features/issues/components/property-block-view';

const PROPERTY_BLOCK_PLUGIN_KEY = new PluginKey('propertyBlockEnforcement');

export const PropertyBlockNode = Node.create({
  name: 'propertyBlock',
  group: 'block',
  atom: true,
  draggable: false,
  selectable: true,
  isolating: true,
  defining: true,

  addAttributes() {
    return {
      issueId: { default: null },
      collapsed: { default: false },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-property-block]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', { ...HTMLAttributes, 'data-property-block': '' }, 0];
  },

  addNodeView() {
    return ReactNodeViewRenderer(PropertyBlockView);
  },

  addProseMirrorPlugins() {
    const nodeType = this.type;

    return [
      new Plugin({
        key: PROPERTY_BLOCK_PLUGIN_KEY,
        appendTransaction(_transactions, _oldState, newState) {
          const { doc, tr } = newState;
          const firstNode = doc.firstChild;

          // If the first node is not a propertyBlock, re-insert it
          if (!firstNode || firstNode.type.name !== nodeType.name) {
            tr.insert(0, nodeType.create());
            return tr;
          }

          return null;
        },
      }),
    ];
  },
});

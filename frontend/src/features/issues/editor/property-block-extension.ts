/**
 * PropertyBlockNode - Custom TipTap Node extension for inline issue properties.
 *
 * Renders as an atom node at document position 0. The node is guaranteed
 * by prepending `<div data-property-block></div>` to the editor's initial
 * HTML content (see IssueDetailPage).
 *
 * Uses ReactNodeViewRenderer for the PropertyBlockView component.
 * Data flows through IssueNoteContext (React context), NOT through
 * TipTap node attributes, to avoid serialization overhead.
 */
import { Node } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { ReactNodeViewRenderer } from '@tiptap/react';
import { PropertyBlockView } from '@/features/issues/components/property-block-view';

const propertyBlockGuardKey = new PluginKey('propertyBlockGuard');

export const PropertyBlockNode = Node.create({
  name: 'propertyBlock',
  group: 'block',
  atom: true,
  draggable: false,
  selectable: false,
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
    return ['div', { ...HTMLAttributes, 'data-property-block': '' }];
  },

  addNodeView() {
    // Note: TipTap's ReactRenderer calls flushSync when editor.isInitialized,
    // producing a harmless React warning. This is a known TipTap limitation
    // (see @tiptap/react/src/ReactRenderer.tsx:188-191).
    return ReactNodeViewRenderer(PropertyBlockView);
  },

  addProseMirrorPlugins() {
    const typeName = this.name;

    return [
      new Plugin({
        key: propertyBlockGuardKey,

        // Block any transaction that would remove the propertyBlock node.
        filterTransaction(tr, state) {
          // Allow non-docChanged transactions (selection, metadata-only).
          if (!tr.docChanged) return true;

          const hasPropertyBlock = (doc: typeof state.doc) => {
            let found = false;
            doc.descendants((node) => {
              if (node.type.name === typeName) found = true;
              return !found;
            });
            return found;
          };

          const hadBefore = hasPropertyBlock(state.doc);
          const hasAfter = hasPropertyBlock(tr.doc);

          // If the property block existed and would be removed, reject.
          if (hadBefore && !hasAfter) return false;

          return true;
        },

        // Safety net: re-insert propertyBlock at position 0 if missing.
        appendTransaction(_trs, _oldState, newState) {
          let found = false;
          newState.doc.descendants((node) => {
            if (node.type.name === typeName) found = true;
            return !found;
          });

          if (!found) {
            const nodeType = newState.schema.nodes[typeName];
            if (!nodeType) return null;
            const tr = newState.tr.insert(0, nodeType.create());
            tr.setMeta('addToHistory', false);
            return tr;
          }

          return null;
        },
      }),
    ];
  },
});

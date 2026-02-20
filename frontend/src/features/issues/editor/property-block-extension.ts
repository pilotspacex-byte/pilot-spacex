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
import { ReactNodeViewRenderer } from '@tiptap/react';
import { PropertyBlockView } from '@/features/issues/components/property-block-view';

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
    return ReactNodeViewRenderer(PropertyBlockView);
  },
});

/**
 * InlineIssueExtension - TipTap Node for inline issue references
 *
 * Per UI Spec v3.3 / DD-013 Note-First workflow:
 * - Rainbow gradient border for active issues
 * - Green border for completed issues
 * - Hover shows issue details card
 * - Bidirectional sync with issue state
 *
 * @see DD-013 Note-First Collaborative Workspace
 * @see UI Spec v3.3 Section 7 - Issue Extraction Flow
 */
import { Node, mergeAttributes } from '@tiptap/core';
import { ReactNodeViewRenderer } from '@tiptap/react';
import { InlineIssueComponent } from './InlineIssueComponent';

/**
 * Issue type options
 */
export type IssueType = 'bug' | 'improvement' | 'feature' | 'task';

/**
 * Issue state options
 */
export type IssueState = 'backlog' | 'todo' | 'in_progress' | 'in_review' | 'done' | 'cancelled';

/**
 * Issue priority options
 */
export type IssuePriority = 'urgent' | 'high' | 'medium' | 'low' | 'none';

/**
 * Inline issue attributes stored in the document
 */
export interface InlineIssueAttributes {
  /** Issue UUID */
  issueId: string;
  /** Issue key/identifier (e.g., PS-201) */
  issueKey: string;
  /** Issue title */
  title: string;
  /** Issue type */
  type: IssueType;
  /** Issue state */
  state: IssueState;
  /** Issue priority */
  priority: IssuePriority;
  /** Source block ID this issue was extracted from */
  sourceBlockId?: string;
  /** Whether this is a newly created issue (shows rainbow animation) */
  isNew?: boolean;
}

export interface InlineIssueOptions {
  /** Callback when issue is clicked */
  onIssueClick?: (issueId: string) => void;
  /** Callback when issue hover starts (for fetching details) */
  onIssueHover?: (issueId: string) => Promise<InlineIssueAttributes | null>;
  /** Callback when user wants to remove the issue link */
  onIssueUnlink?: (issueId: string) => void;
  /** Custom class for the node */
  HTMLAttributes?: Record<string, unknown>;
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    inlineIssue: {
      /**
       * Insert an inline issue reference
       */
      insertInlineIssue: (attributes: InlineIssueAttributes) => ReturnType;
      /**
       * Update an existing inline issue
       */
      updateInlineIssue: (
        issueId: string,
        attributes: Partial<InlineIssueAttributes>
      ) => ReturnType;
      /**
       * Remove an inline issue by ID
       */
      removeInlineIssue: (issueId: string) => ReturnType;
    };
  }
}

/**
 * InlineIssueExtension creates inline issue references with rainbow borders
 *
 * @example
 * ```tsx
 * import { InlineIssueExtension } from './extensions/InlineIssueExtension';
 *
 * const editor = new Editor({
 *   extensions: [
 *     InlineIssueExtension.configure({
 *       onIssueClick: (issueId) => {
 *         router.push(`/issues/${issueId}`);
 *       },
 *     }),
 *   ],
 * });
 *
 * // Insert an issue reference
 * editor.commands.insertInlineIssue({
 *   issueId: 'uuid-123',
 *   issueKey: 'PS-201',
 *   title: 'Simplify password reset',
 *   type: 'bug',
 *   state: 'todo',
 *   priority: 'medium',
 *   isNew: true,
 * });
 * ```
 */
export const InlineIssueExtension = Node.create<InlineIssueOptions>({
  name: 'inlineIssue',

  group: 'inline',

  inline: true,

  atom: true, // Cannot be edited directly

  selectable: true,

  draggable: true,

  addOptions() {
    return {
      onIssueClick: undefined,
      onIssueHover: undefined,
      onIssueUnlink: undefined,
      HTMLAttributes: {},
    };
  },

  addAttributes() {
    return {
      issueId: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-issue-id'),
        renderHTML: (attributes) => ({
          'data-issue-id': attributes.issueId as string,
        }),
      },
      issueKey: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-issue-key'),
        renderHTML: (attributes) => ({
          'data-issue-key': attributes.issueKey as string,
        }),
      },
      title: {
        default: '',
        parseHTML: (element) => element.getAttribute('data-title'),
        renderHTML: (attributes) => ({
          'data-title': attributes.title as string,
        }),
      },
      type: {
        default: 'task',
        parseHTML: (element) => element.getAttribute('data-type'),
        renderHTML: (attributes) => ({
          'data-type': attributes.type as string,
        }),
      },
      state: {
        default: 'todo',
        parseHTML: (element) => element.getAttribute('data-state'),
        renderHTML: (attributes) => ({
          'data-state': attributes.state as string,
        }),
      },
      priority: {
        default: 'none',
        parseHTML: (element) => element.getAttribute('data-priority'),
        renderHTML: (attributes) => ({
          'data-priority': attributes.priority as string,
        }),
      },
      sourceBlockId: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-source-block-id'),
        renderHTML: (attributes) => {
          if (!attributes.sourceBlockId) return {};
          return {
            'data-source-block-id': attributes.sourceBlockId as string,
          };
        },
      },
      isNew: {
        default: false,
        parseHTML: (element) => element.getAttribute('data-is-new') === 'true',
        renderHTML: (attributes) => {
          if (!attributes.isNew) return {};
          return { 'data-is-new': 'true' };
        },
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'span[data-type="inline-issue"]',
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'span',
      mergeAttributes(this.options.HTMLAttributes ?? {}, HTMLAttributes, {
        'data-type': 'inline-issue',
        class: 'inline-issue-node',
      }),
    ];
  },

  addNodeView() {
    return ReactNodeViewRenderer(InlineIssueComponent);
  },

  addCommands() {
    return {
      insertInlineIssue:
        (attributes: InlineIssueAttributes) =>
        ({ commands }) => {
          return commands.insertContent({
            type: this.name,
            attrs: attributes,
          });
        },

      updateInlineIssue:
        (issueId: string, attributes: Partial<InlineIssueAttributes>) =>
        ({ tr, state, dispatch }) => {
          let found = false;

          state.doc.descendants((node, pos) => {
            if (node.type.name === this.name && node.attrs.issueId === issueId) {
              if (dispatch) {
                const newAttrs = { ...node.attrs, ...attributes };
                tr.setNodeMarkup(pos, undefined, newAttrs);
              }
              found = true;
              return false; // Stop iteration
            }
            return true;
          });

          return found;
        },

      removeInlineIssue:
        (issueId: string) =>
        ({ tr, state, dispatch }) => {
          let found = false;

          state.doc.descendants((node, pos) => {
            if (node.type.name === this.name && node.attrs.issueId === issueId) {
              if (dispatch) {
                tr.delete(pos, pos + node.nodeSize);
              }
              found = true;
              return false; // Stop iteration
            }
            return true;
          });

          return found;
        },
    };
  },

  addKeyboardShortcuts() {
    return {
      // Backspace deletes selected inline issue
      Backspace: () => {
        const { selection } = this.editor.state;
        const { $from } = selection;

        // Check if we're right after an inline issue
        const nodeBefore = $from.nodeBefore;
        if (nodeBefore?.type.name === this.name) {
          return this.editor.commands.deleteRange({
            from: $from.pos - nodeBefore.nodeSize,
            to: $from.pos,
          });
        }

        return false;
      },
    };
  },
});

export default InlineIssueExtension;

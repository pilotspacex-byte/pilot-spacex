/**
 * NoteLinkExtension - Wiki-style note-to-note linking with [[ trigger
 *
 * Creates an inline atom node `noteLink` that:
 * - Triggers autocomplete on `[[` input
 * - Stores only `noteId` (title resolved at render time via R-4 fix)
 * - Renders as inline chip via React NodeView (NoteLinkComponent)
 * - Supports markdown serialization: [note-title](note:uuid)
 *
 * Pattern: Follows MentionExtension (suggestion popup) + InlineIssueExtension (atom node)
 *
 * @see tmp/note-editor-plan.md Section 1d
 * @see tmp/note-editor-ui-design.md Section 4a
 */
import { Node, mergeAttributes, type Editor, type Range } from '@tiptap/core';
import { ReactNodeViewRenderer } from '@tiptap/react';
import { Node as ProseMirrorNode } from '@tiptap/pm/model';
import Suggestion, { type SuggestionProps, type SuggestionKeyDownProps } from '@tiptap/suggestion';
import tippy, { type Instance as TippyInstance } from 'tippy.js';
import type { MarkdownNodeSpec } from 'tiptap-markdown';
import type { MarkdownSerializerState } from 'prosemirror-markdown';
import { NoteLinkComponent } from './NoteLinkComponent';

export interface NoteLinkSearchResult {
  id: string;
  title: string;
  updatedAt: string;
}

export interface NoteLinkOptions {
  /** Workspace slug for building navigation URLs */
  workspaceSlug: string;
  /** Current note ID — excluded from search results (R-9: prevent self-links) */
  currentNoteId: string;
  /** Search function for note autocomplete */
  onSearch: (query: string) => Promise<NoteLinkSearchResult[]>;
  /** Callback when a note link is inserted (to persist via API) */
  onLinkCreated?: (targetNoteId: string, blockId?: string) => void;
  /** Callback when a note link is clicked */
  onClick?: (noteId: string) => void;
  /** Maximum suggestions to show */
  maxSuggestions: number;
  /** Debounce time for search */
  debounceMs: number;
  /** Custom HTML attributes for the node */
  HTMLAttributes: Record<string, unknown>;
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    noteLink: {
      /** Insert an inline note link */
      insertNoteLink: (noteId: string) => ReturnType;
    };
  }
}

/**
 * Creates the note search suggestion list popup (vanilla DOM, like MentionExtension)
 */
function createNoteLinkListElement(props: {
  items: NoteLinkSearchResult[];
  command: (item: { id: string }) => void;
  selectedIndex: number;
}): HTMLElement {
  const container = document.createElement('div');
  container.className = 'note-link-suggestion-list';
  container.setAttribute('role', 'listbox');
  container.setAttribute('aria-label', 'Note search results');

  if (props.items.length === 0) {
    const empty = document.createElement('div');
    empty.textContent = 'No notes found';
    empty.className = 'note-link-suggestion-empty';
    container.appendChild(empty);
    return container;
  }

  props.items.forEach((item, index) => {
    const button = document.createElement('button');
    button.setAttribute('role', 'option');
    button.setAttribute('aria-selected', String(index === props.selectedIndex));
    button.setAttribute('type', 'button');

    button.className = 'note-link-suggestion-item';

    // FileText icon (SVG)
    const iconSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    iconSvg.setAttribute('width', '14');
    iconSvg.setAttribute('height', '14');
    iconSvg.setAttribute('viewBox', '0 0 24 24');
    iconSvg.setAttribute('fill', 'none');
    iconSvg.setAttribute('stroke', 'currentColor');
    iconSvg.setAttribute('stroke-width', '2');
    iconSvg.setAttribute('stroke-linecap', 'round');
    iconSvg.setAttribute('stroke-linejoin', 'round');
    iconSvg.classList.add('note-link-suggestion-item-icon');
    iconSvg.innerHTML =
      '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>' +
      '<path d="M14 2v4a2 2 0 0 0 2 2h4"/>' +
      '<path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>';
    button.appendChild(iconSvg);

    // Text container
    const info = document.createElement('div');
    info.className = 'note-link-suggestion-item-info';

    const title = document.createElement('div');
    title.textContent = item.title || 'Untitled';
    title.className = 'note-link-suggestion-item-title';

    const subtitle = document.createElement('div');
    const updatedDate = new Date(item.updatedAt);
    const now = new Date();
    const diffMs = now.getTime() - updatedDate.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    let timeAgo: string;
    if (diffMins < 1) timeAgo = 'just now';
    else if (diffMins < 60) timeAgo = `${diffMins}m ago`;
    else if (diffHours < 24) timeAgo = `${diffHours}h ago`;
    else timeAgo = `${diffDays}d ago`;
    subtitle.textContent = `Updated ${timeAgo}`;
    subtitle.className = 'note-link-suggestion-item-subtitle';

    info.appendChild(title);
    info.appendChild(subtitle);
    button.appendChild(info);

    button.addEventListener('click', () => {
      props.command({ id: item.id });
    });

    container.appendChild(button);
  });

  return container;
}

export const NoteLinkExtension = Node.create<NoteLinkOptions>({
  name: 'noteLink',

  group: 'inline',

  inline: true,

  atom: true,

  selectable: true,

  draggable: true,

  addOptions() {
    return {
      workspaceSlug: '',
      currentNoteId: '',
      onSearch: async () => [],
      onLinkCreated: undefined,
      onClick: undefined,
      maxSuggestions: 10,
      debounceMs: 150,
      HTMLAttributes: {},
    };
  },

  addStorage() {
    return {
      noteTitles: new Map<string, string>(),
      markdown: {
        serialize(state: MarkdownSerializerState, node: ProseMirrorNode) {
          const noteId = (node.attrs.noteId as string) || '';
          // Title is not stored in attrs (R-4); use placeholder
          state.write(`[note](note:${noteId})`);
        },
        parse: {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          setup(markdownit: any) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            markdownit.inline.ruler.before('link', 'note_link', (state: any) => {
              const start = state.pos;
              const max = state.posMax;

              if (state.src.charCodeAt(start) !== 0x5b) return false;

              let labelEnd = -1;
              for (let i = start + 1; i < max; i++) {
                if (state.src.charCodeAt(i) === 0x5d) {
                  labelEnd = i;
                  break;
                }
              }
              if (labelEnd === -1) return false;

              const linkStart = labelEnd + 1;
              if (
                linkStart >= max ||
                state.src.charCodeAt(linkStart) !== 0x28 ||
                !state.src.startsWith('note:', linkStart + 1)
              ) {
                return false;
              }

              let linkEnd = -1;
              for (let i = linkStart + 6; i < max; i++) {
                if (state.src.charCodeAt(i) === 0x29) {
                  linkEnd = i;
                  break;
                }
              }
              if (linkEnd === -1) return false;

              const noteId = state.src.slice(linkStart + 6, linkEnd).trim();
              if (!noteId) return false;

              const token = state.push('note_link', '', 0);
              token.attrs = [['noteId', noteId]];
              state.pos = linkEnd + 1;
              return true;
            });
          },
        },
      } as MarkdownNodeSpec,
    };
  },

  addAttributes() {
    return {
      noteId: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-note-id'),
        renderHTML: (attributes) => ({
          'data-note-id': attributes.noteId as string,
        }),
      },
    };
  },

  parseHTML() {
    return [{ tag: 'span[data-type="note-link"]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'span',
      mergeAttributes(this.options.HTMLAttributes, HTMLAttributes, {
        'data-type': 'note-link',
        class: 'note-link-node',
      }),
    ];
  },

  addNodeView() {
    return ReactNodeViewRenderer(NoteLinkComponent);
  },

  addCommands() {
    return {
      insertNoteLink:
        (noteId: string) =>
        ({ commands }) => {
          return commands.insertContent({
            type: this.name,
            attrs: { noteId },
          });
        },
    };
  },

  addKeyboardShortcuts() {
    return {
      Backspace: () => {
        const { selection } = this.editor.state;
        const { $from } = selection;
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

  addProseMirrorPlugins() {
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    const extension = this;
    let searchTimeout: ReturnType<typeof setTimeout> | null = null;
    let popup: TippyInstance | null = null;
    let component: HTMLElement | null = null;
    let selectedIndex = 0;
    let items: NoteLinkSearchResult[] = [];
    let currentCommand: ((attrs: { id: string }) => void) | null = null;

    const suggestionConfig = {
      char: '[[',
      allowSpaces: true,
      startOfLine: false,

      items: async ({ query }: { query: string; editor: Editor }) => {
        if (searchTimeout) clearTimeout(searchTimeout);

        return new Promise<NoteLinkSearchResult[]>((resolve) => {
          searchTimeout = setTimeout(async () => {
            try {
              const results = await extension.options.onSearch(query);
              // R-9: Exclude current note from autocomplete (prevent self-links)
              const currentId = extension.options.currentNoteId;
              const filtered = currentId ? results.filter((r) => r.id !== currentId) : results;
              items = filtered.slice(0, extension.options.maxSuggestions);
              resolve(items);
            } catch {
              resolve([]);
            }
          }, extension.options.debounceMs);
        });
      },

      command: ({
        editor,
        range,
        props: itemProps,
      }: {
        editor: Editor;
        range: Range;
        props: { id: string };
      }) => {
        // Resolve the containing block's ID before inserting (for link persistence)
        let blockId: string | undefined;
        const $pos = editor.state.doc.resolve(range.from);
        for (let d = $pos.depth; d >= 0; d--) {
          const ancestor = $pos.node(d);
          const bid = (ancestor.attrs?.id ?? ancestor.attrs?.blockId) as string | undefined;
          if (bid) {
            blockId = bid;
            break;
          }
        }

        // Cache the selected note's title in storage before inserting
        const selectedItem = items.find((i) => i.id === itemProps.id);
        if (selectedItem) {
          const titleMap = extension.storage.noteTitles as Map<string, string>;
          titleMap.set(selectedItem.id, selectedItem.title);
        }

        editor.chain().focus().deleteRange(range).insertNoteLink(itemProps.id).run();

        extension.options.onLinkCreated?.(itemProps.id, blockId);
      },

      render: () => {
        return {
          onStart: (props: SuggestionProps<NoteLinkSearchResult, { id: string }>) => {
            selectedIndex = 0;
            currentCommand = props.command;

            component = createNoteLinkListElement({
              items,
              command: (item) => props.command(item),
              selectedIndex,
            });

            if (!props.clientRect) return;
            const rect = props.clientRect();
            if (!rect) return;

            popup = tippy(document.body, {
              getReferenceClientRect: () => rect,
              appendTo: () => document.body,
              content: component,
              showOnCreate: true,
              interactive: true,
              trigger: 'manual',
              placement: 'bottom-start',
              animation: 'shift-away',
            });
          },

          onUpdate: (props: SuggestionProps<NoteLinkSearchResult, { id: string }>) => {
            currentCommand = props.command;

            component = createNoteLinkListElement({
              items,
              command: (item) => props.command(item),
              selectedIndex,
            });

            if (popup) popup.setContent(component);
            if (props.clientRect) {
              const rect = props.clientRect();
              if (rect) popup?.setProps({ getReferenceClientRect: () => rect });
            }
          },

          onKeyDown: (props: SuggestionKeyDownProps) => {
            if (props.event.key === 'ArrowUp') {
              selectedIndex = (selectedIndex - 1 + items.length) % items.length;
              if (component && currentCommand) {
                const newEl = createNoteLinkListElement({
                  items,
                  command: (item) => currentCommand!(item),
                  selectedIndex,
                });
                popup?.setContent(newEl);
                component = newEl;
              }
              return true;
            }

            if (props.event.key === 'ArrowDown') {
              selectedIndex = (selectedIndex + 1) % items.length;
              if (component && currentCommand) {
                const newEl = createNoteLinkListElement({
                  items,
                  command: (item) => currentCommand!(item),
                  selectedIndex,
                });
                popup?.setContent(newEl);
                component = newEl;
              }
              return true;
            }

            if (props.event.key === 'Enter') {
              const item = items[selectedIndex];
              if (item && currentCommand) {
                currentCommand({ id: item.id });
                return true;
              }
            }

            if (props.event.key === 'Escape') {
              popup?.hide();
              return true;
            }

            return false;
          },

          onExit: () => {
            popup?.destroy();
            popup = null;
            component = null;
            selectedIndex = 0;
            items = [];
            currentCommand = null;
          },
        };
      },
    };

    return [Suggestion({ editor: this.editor, ...suggestionConfig })];
  },
});

export default NoteLinkExtension;

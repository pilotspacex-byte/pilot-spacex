/**
 * MentionExtension - User mentions with @ trigger
 *
 * Features:
 * - Trigger on @ character
 * - User search popup (workspace members)
 * - Styled chip with avatar
 * - Keyboard navigation in popup
 */
import Mention from '@tiptap/extension-mention';
import tippy, { type Instance as TippyInstance } from 'tippy.js';

/**
 * Mention suggestion user data
 */
export interface MentionUser {
  id: string;
  name: string;
  email: string;
  avatarUrl?: string;
}

export interface MentionOptions {
  /** Trigger character (default: '@') */
  trigger: string;
  /** CSS class for mention chips */
  className: string;
  /** Search function for users */
  onSearch: (query: string) => Promise<MentionUser[]>;
  /** Callback when mention is selected */
  onSelect?: (user: MentionUser) => void;
  /** Maximum suggestions to show */
  maxSuggestions: number;
  /** Debounce time for search */
  debounceMs: number;
}

interface MentionListProps {
  items: MentionUser[];
  command: (item: { id: string; label: string }) => void;
  selectedIndex: number;
}

/**
 * Creates the mention list popup component
 */
function createMentionListElement(props: MentionListProps): HTMLElement {
  const container = document.createElement('div');
  container.className = 'mention-list';
  container.setAttribute('role', 'listbox');
  container.style.cssText = `
    background: var(--popover, white);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    padding: 4px;
    min-width: 200px;
    max-height: 300px;
    overflow-y: auto;
  `;

  if (props.items.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'mention-list-empty';
    empty.textContent = 'No users found';
    empty.style.cssText = `
      padding: 8px 12px;
      color: var(--muted-foreground, #6b7280);
      font-size: 14px;
    `;
    container.appendChild(empty);
    return container;
  }

  props.items.forEach((item, index) => {
    const button = document.createElement('button');
    button.className = `mention-list-item ${index === props.selectedIndex ? 'is-selected' : ''}`;
    button.setAttribute('role', 'option');
    button.setAttribute('aria-selected', String(index === props.selectedIndex));
    button.setAttribute('type', 'button');

    const isSelected = index === props.selectedIndex;
    button.style.cssText = `
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      padding: 8px 12px;
      border: none;
      border-radius: 6px;
      background: ${isSelected ? 'var(--accent, #f3f4f6)' : 'transparent'};
      cursor: pointer;
      text-align: left;
      font-size: 14px;
      color: var(--foreground, #111827);
      transition: background-color 0.15s ease;
    `;

    // Avatar
    if (item.avatarUrl) {
      const avatar = document.createElement('img');
      avatar.src = item.avatarUrl;
      avatar.alt = item.name;
      avatar.style.cssText = `
        width: 28px;
        height: 28px;
        border-radius: 50%;
        object-fit: cover;
      `;
      button.appendChild(avatar);
    } else {
      // Fallback avatar with initials
      const avatar = document.createElement('div');
      avatar.style.cssText = `
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background: var(--primary, #3b82f6);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: 600;
      `;
      avatar.textContent = item.name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);
      button.appendChild(avatar);
    }

    // Name and email
    const info = document.createElement('div');
    info.style.cssText = 'flex: 1; min-width: 0;';

    const name = document.createElement('div');
    name.textContent = item.name;
    name.style.cssText = `
      font-weight: 500;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    `;

    const email = document.createElement('div');
    email.textContent = item.email;
    email.style.cssText = `
      font-size: 12px;
      color: var(--muted-foreground, #6b7280);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    `;

    info.appendChild(name);
    info.appendChild(email);
    button.appendChild(info);

    // Hover effect
    button.addEventListener('mouseenter', () => {
      button.style.backgroundColor = 'var(--accent, #f3f4f6)';
    });
    button.addEventListener('mouseleave', () => {
      if (!isSelected) {
        button.style.backgroundColor = 'transparent';
      }
    });

    // Click handler
    button.addEventListener('click', () => {
      props.command({ id: item.id, label: item.name });
    });

    container.appendChild(button);
  });

  return container;
}

/**
 * MentionExtension with user search and styled chips
 *
 * @example
 * ```tsx
 * import { MentionExtension } from './extensions/MentionExtension';
 *
 * const editor = new Editor({
 *   extensions: [
 *     MentionExtension.configure({
 *       onSearch: async (query) => {
 *         const response = await fetch(`/api/users?search=${query}`);
 *         return response.json();
 *       },
 *       onSelect: (user) => {
 *         console.log('Mentioned user:', user);
 *       },
 *     }),
 *   ],
 * });
 * ```
 */
export const MentionExtension = Mention.extend<MentionOptions>({
  addOptions() {
    return {
      ...this.parent?.(),
      trigger: '@',
      className: 'mention-chip',
      onSearch: async () => [],
      onSelect: undefined,
      maxSuggestions: 10,
      debounceMs: 150,
      HTMLAttributes: {
        class: 'mention-chip',
      },
      renderLabel({ node }: { node: { attrs: { label?: string; id?: string } } }) {
        return `@${node.attrs.label ?? node.attrs.id ?? ''}`;
      },
      suggestion: {
        char: '@',
        allowSpaces: false,
        startOfLine: false,
        items: async () => {
          // This will be overridden below
          return [];
        },
        render: () => {
          // This will be overridden below
          return {};
        },
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
    let items: MentionUser[] = [];

    // Override the suggestion configuration
    const suggestionConfig = {
      char: extension.options.trigger,
      allowSpaces: false,
      startOfLine: false,

      items: async ({ query }: { query: string }) => {
        // Clear existing timeout
        if (searchTimeout) {
          clearTimeout(searchTimeout);
        }

        // Debounced search
        return new Promise((resolve) => {
          searchTimeout = setTimeout(async () => {
            try {
              const results = await extension.options.onSearch(query);
              items = results.slice(0, extension.options.maxSuggestions);
              resolve(items);
            } catch {
              resolve([]);
            }
          }, extension.options.debounceMs);
        });
      },

      render: () => {
        return {
          onStart: (props: {
            clientRect: (() => DOMRect) | null;
            command: (item: { id: string; label: string }) => void;
          }) => {
            selectedIndex = 0;

            component = createMentionListElement({
              items,
              command: (item) => {
                props.command(item);
                const user = items.find((u) => u.id === item.id);
                if (user) {
                  extension.options.onSelect?.(user);
                }
              },
              selectedIndex,
            });

            if (!props.clientRect) {
              return;
            }

            popup = tippy(document.body, {
              getReferenceClientRect: props.clientRect,
              appendTo: () => document.body,
              content: component,
              showOnCreate: true,
              interactive: true,
              trigger: 'manual',
              placement: 'bottom-start',
              animation: 'shift-away',
            });
          },

          onUpdate: (props: {
            clientRect: (() => DOMRect) | null;
            command: (item: { id: string; label: string }) => void;
          }) => {
            component = createMentionListElement({
              items,
              command: (item) => {
                props.command(item);
                const user = items.find((u) => u.id === item.id);
                if (user) {
                  extension.options.onSelect?.(user);
                }
              },
              selectedIndex,
            });

            if (popup) {
              popup.setContent(component);
            }

            if (props.clientRect) {
              popup?.setProps({
                getReferenceClientRect: props.clientRect,
              });
            }
          },

          onKeyDown: (props: { event: KeyboardEvent }) => {
            if (props.event.key === 'ArrowUp') {
              selectedIndex = (selectedIndex - 1 + items.length) % items.length;
              return true;
            }

            if (props.event.key === 'ArrowDown') {
              selectedIndex = (selectedIndex + 1) % items.length;
              return true;
            }

            if (props.event.key === 'Enter') {
              const item = items[selectedIndex];
              if (item) {
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
          },
        };
      },
    };

    // Apply the suggestion config
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (this.options as any).suggestion = suggestionConfig;

    return this.parent?.() ?? [];
  },
});

/**
 * CSS styles for mentions (add to your global stylesheet)
 */
export const mentionStyles = `
  .mention-chip {
    display: inline;
    padding: 2px 6px;
    border-radius: 4px;
    background-color: var(--primary-foreground, rgba(59, 130, 246, 0.1));
    color: var(--primary, #3b82f6);
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.15s ease;
  }

  .mention-chip:hover {
    background-color: var(--primary-foreground-hover, rgba(59, 130, 246, 0.2));
  }

  .mention-list {
    animation: mention-list-fade-in 0.15s ease;
  }

  @keyframes mention-list-fade-in {
    from {
      opacity: 0;
      transform: translateY(-4px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .mention-list-item.is-selected {
    background: var(--accent, #f3f4f6);
  }
`;

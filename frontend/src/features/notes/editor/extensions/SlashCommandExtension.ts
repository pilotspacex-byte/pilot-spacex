/**
 * SlashCommandExtension - Slash commands for quick formatting and AI actions
 *
 * Features:
 * - Trigger on / at start of line
 * - Commands: /heading, /code, /quote, /bullet, /todo, /divider
 * - AI commands: /ai-improve, /ai-summarize, /ai-extract-issues
 * - Keyboard navigation (Arrow keys, Enter, Escape)
 */
import { Extension, type Editor } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';

/**
 * Slash command definition
 */
export interface SlashCommand {
  /** Command name (e.g., 'heading') */
  name: string;
  /** Display label */
  label: string;
  /** Description for menu */
  description: string;
  /** Icon name (Lucide icon) */
  icon: string;
  /** Command group */
  group: 'formatting' | 'blocks' | 'ai';
  /** Keyboard shortcut hint */
  shortcut?: string;
  /** Execute the command */
  execute: (editor: Editor) => void;
  /** Search keywords */
  keywords?: string[];
}

export interface SlashCommandOptions {
  /** Custom commands to add or override */
  commands?: SlashCommand[];
  /** Callback when command is executed */
  onExecute?: (command: SlashCommand) => void;
  /** AI command handler */
  onAICommand?: (command: string, editor: Editor) => Promise<void>;
  /** Maximum suggestions to show */
  maxSuggestions: number;
}

interface SlashCommandPluginState {
  isActive: boolean;
  query: string;
  position: number | null;
  selectedIndex: number;
}

const SLASH_COMMAND_PLUGIN_KEY = new PluginKey<SlashCommandPluginState>('slashCommand');

/**
 * Default slash commands
 */
function getDefaultCommands(
  onAICommand?: (command: string, editor: Editor) => Promise<void>
): SlashCommand[] {
  return [
    // Formatting commands
    {
      name: 'heading1',
      label: 'Heading 1',
      description: 'Large section heading',
      icon: 'Heading1',
      group: 'formatting',
      shortcut: '# ',
      keywords: ['h1', 'title', 'large'],
      execute: (editor) => editor.chain().focus().toggleHeading({ level: 1 }).run(),
    },
    {
      name: 'heading2',
      label: 'Heading 2',
      description: 'Medium section heading',
      icon: 'Heading2',
      group: 'formatting',
      shortcut: '## ',
      keywords: ['h2', 'subtitle', 'medium'],
      execute: (editor) => editor.chain().focus().toggleHeading({ level: 2 }).run(),
    },
    {
      name: 'heading3',
      label: 'Heading 3',
      description: 'Small section heading',
      icon: 'Heading3',
      group: 'formatting',
      shortcut: '### ',
      keywords: ['h3', 'small'],
      execute: (editor) => editor.chain().focus().toggleHeading({ level: 3 }).run(),
    },

    // Block commands
    {
      name: 'bullet',
      label: 'Bullet List',
      description: 'Create a simple bullet list',
      icon: 'List',
      group: 'blocks',
      shortcut: '- ',
      keywords: ['ul', 'unordered', 'list'],
      execute: (editor) => editor.chain().focus().toggleBulletList().run(),
    },
    {
      name: 'numbered',
      label: 'Numbered List',
      description: 'Create a numbered list',
      icon: 'ListOrdered',
      group: 'blocks',
      shortcut: '1. ',
      keywords: ['ol', 'ordered', 'number'],
      execute: (editor) => editor.chain().focus().toggleOrderedList().run(),
    },
    {
      name: 'todo',
      label: 'Todo List',
      description: 'Track tasks with a todo list',
      icon: 'CheckSquare',
      group: 'blocks',
      keywords: ['checkbox', 'task', 'check'],
      execute: (editor) => editor.chain().focus().toggleTaskList().run(),
    },
    {
      name: 'quote',
      label: 'Quote',
      description: 'Capture a quote',
      icon: 'Quote',
      group: 'blocks',
      shortcut: '> ',
      keywords: ['blockquote', 'citation'],
      execute: (editor) => editor.chain().focus().toggleBlockquote().run(),
    },
    {
      name: 'code',
      label: 'Code Block',
      description: 'Capture a code snippet',
      icon: 'Code',
      group: 'blocks',
      shortcut: '```',
      keywords: ['codeblock', 'snippet', 'programming'],
      execute: (editor) => editor.chain().focus().toggleCodeBlock().run(),
    },
    {
      name: 'divider',
      label: 'Divider',
      description: 'Visually divide blocks',
      icon: 'Minus',
      group: 'blocks',
      shortcut: '---',
      keywords: ['hr', 'horizontal', 'line', 'separator'],
      execute: (editor) => editor.chain().focus().setHorizontalRule().run(),
    },

    // AI commands
    {
      name: 'ai-improve',
      label: 'AI: Improve Writing',
      description: 'Improve selected text with AI',
      icon: 'Sparkles',
      group: 'ai',
      keywords: ['enhance', 'rewrite', 'polish'],
      execute: (editor) => {
        if (onAICommand) {
          onAICommand('improve', editor);
        }
      },
    },
    {
      name: 'ai-summarize',
      label: 'AI: Summarize',
      description: 'Summarize the document',
      icon: 'FileText',
      group: 'ai',
      keywords: ['summary', 'tldr', 'brief'],
      execute: (editor) => {
        if (onAICommand) {
          onAICommand('summarize', editor);
        }
      },
    },
    {
      name: 'ai-extract-issues',
      label: 'AI: Extract Issues',
      description: 'Find potential issues to create',
      icon: 'ListTodo',
      group: 'ai',
      keywords: ['issues', 'tasks', 'tickets', 'extract'],
      execute: (editor) => {
        if (onAICommand) {
          onAICommand('extract-issues', editor);
        }
      },
    },
  ];
}

/**
 * Filter commands by query
 */
function filterCommands(commands: SlashCommand[], query: string): SlashCommand[] {
  if (!query) return commands;

  const lowerQuery = query.toLowerCase();
  return commands.filter((cmd) => {
    const matchesName = cmd.name.toLowerCase().includes(lowerQuery);
    const matchesLabel = cmd.label.toLowerCase().includes(lowerQuery);
    const matchesKeywords = cmd.keywords?.some((k) => k.toLowerCase().includes(lowerQuery));
    return matchesName || matchesLabel || matchesKeywords;
  });
}

/**
 * Helper to create a kbd element for keyboard hints
 */
function createKbd(text: string): HTMLElement {
  const kbd = document.createElement('kbd');
  kbd.textContent = text;
  kbd.style.cssText = `
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 16px;
    height: 16px;
    padding: 0 4px;
    background: var(--muted, hsl(240 5% 15%));
    border: 1px solid var(--border, hsl(240 5% 22%));
    border-radius: 3px;
    font-family: inherit;
    font-size: 9px;
    font-weight: 500;
  `;
  return kbd;
}

/**
 * Creates the slash command menu element - Claude Code style (compact)
 */
function createCommandMenu(
  commands: SlashCommand[],
  selectedIndex: number,
  editor: Editor,
  onExecute?: (command: SlashCommand) => void,
  onSelect?: (command: SlashCommand) => void
): HTMLElement {
  const container = document.createElement('div');
  container.className = 'slash-command-menu';
  container.setAttribute('role', 'listbox');

  container.style.cssText = `
    position: absolute;
    top: 100%;
    left: 0;
    z-index: 50;
    margin-top: 4px;
    background: var(--popover, hsl(240 10% 8%));
    border: 1px solid var(--border, hsl(240 5% 18%));
    border-radius: 6px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    min-width: 360px;
    max-width: 460px;
    font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);
    font-size: 12px;
    overflow: hidden;
  `;

  if (commands.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'slash-command-empty';
    empty.textContent = 'No commands found';
    empty.style.cssText = `
      padding: 12px 16px;
      color: var(--muted-foreground, hsl(240 5% 45%));
    `;
    container.appendChild(empty);
    return container;
  }

  // Commands list container (scrollable, 5 items visible)
  const listContainer = document.createElement('div');
  listContainer.className = 'slash-command-list';
  listContainer.style.cssText = `
    max-height: 140px;
    overflow-y: auto;
    padding: 4px;
    scrollbar-width: thin;
    scrollbar-color: hsl(240 5% 25%) transparent;
  `;

  commands.forEach((cmd, index) => {
    const isSelected = index === selectedIndex;
    const button = document.createElement('button');
    button.className = `slash-command-item ${isSelected ? 'is-selected' : ''}`;
    button.setAttribute('role', 'option');
    button.setAttribute('aria-selected', String(isSelected));
    button.setAttribute('type', 'button');
    button.setAttribute('data-index', String(index));

    // Primary theme color for selected state
    button.style.cssText = `
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      padding: 6px 8px;
      border: none;
      border-radius: 4px;
      background: ${isSelected ? 'var(--primary, hsl(142 70% 45%))' : 'transparent'};
      cursor: pointer;
      text-align: left;
      font-family: inherit;
      font-size: inherit;
      line-height: 1.3;
      transition: background-color 0.1s;
    `;

    // Selection arrow indicator
    const indicator = document.createElement('span');
    indicator.className = 'slash-command-indicator';
    indicator.textContent = isSelected ? '›' : '';
    indicator.style.cssText = `
      flex-shrink: 0;
      width: 12px;
      font-size: 14px;
      font-weight: bold;
      color: ${isSelected ? 'var(--primary-foreground, white)' : 'transparent'};
    `;

    // Command name
    const cmdName = document.createElement('span');
    cmdName.className = 'slash-command-name';
    cmdName.textContent = `/${cmd.name}`;
    cmdName.style.cssText = `
      flex-shrink: 0;
      min-width: 100px;
      font-weight: 500;
      color: ${isSelected ? 'var(--primary-foreground, white)' : cmd.group === 'ai' ? 'var(--ai, hsl(210 70% 60%))' : 'var(--foreground, hsl(240 5% 85%))'};
    `;

    // Description
    const desc = document.createElement('span');
    desc.className = 'slash-command-desc';
    desc.textContent = cmd.description;
    desc.style.cssText = `
      flex: 1;
      color: ${isSelected ? 'var(--primary-foreground, white)' : 'var(--muted-foreground, hsl(240 5% 50%))'};
      opacity: ${isSelected ? '0.85' : '1'};
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    `;

    button.appendChild(indicator);
    button.appendChild(cmdName);
    button.appendChild(desc);

    // Hover effect
    button.addEventListener('mouseenter', () => {
      if (!isSelected) {
        button.style.backgroundColor = 'var(--accent, hsl(240 5% 15%))';
      }
    });
    button.addEventListener('mouseleave', () => {
      if (!isSelected) {
        button.style.backgroundColor = 'transparent';
      }
    });

    // Click handler
    button.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (onSelect) {
        onSelect(cmd);
      } else {
        cmd.execute(editor);
        onExecute?.(cmd);
      }
    });

    listContainer.appendChild(button);
  });

  container.appendChild(listContainer);

  // Footer with navigation hints
  const footer = document.createElement('div');
  footer.className = 'slash-command-footer';
  footer.style.cssText = `
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 6px 12px;
    border-top: 1px solid var(--border, hsl(240 5% 18%));
    color: var(--muted-foreground, hsl(240 5% 40%));
    font-size: 10px;
  `;

  // Navigation hint
  const navHint = document.createElement('span');
  navHint.style.cssText = 'display: flex; align-items: center; gap: 3px;';
  navHint.appendChild(createKbd('↑'));
  navHint.appendChild(createKbd('↓'));
  const navText = document.createElement('span');
  navText.textContent = ' nav';
  navHint.appendChild(navText);

  // Select hint
  const selectHint = document.createElement('span');
  selectHint.style.cssText = 'display: flex; align-items: center; gap: 3px;';
  selectHint.appendChild(createKbd('↵'));
  const selectText = document.createElement('span');
  selectText.textContent = ' select';
  selectHint.appendChild(selectText);

  // Close hint
  const escHint = document.createElement('span');
  escHint.style.cssText = 'display: flex; align-items: center; gap: 3px;';
  escHint.appendChild(createKbd('esc'));
  const escText = document.createElement('span');
  escText.textContent = ' close';
  escHint.appendChild(escText);

  footer.appendChild(navHint);
  footer.appendChild(selectHint);
  footer.appendChild(escHint);
  container.appendChild(footer);

  // Scroll selected item into view
  requestAnimationFrame(() => {
    const selected = listContainer.querySelector('.is-selected');
    if (selected) {
      selected.scrollIntoView({ block: 'nearest' });
    }
  });

  return container;
}

/**
 * SlashCommandExtension provides quick formatting and AI commands
 *
 * @example
 * ```tsx
 * import { SlashCommandExtension } from './extensions/SlashCommandExtension';
 *
 * const editor = new Editor({
 *   extensions: [
 *     SlashCommandExtension.configure({
 *       onAICommand: async (command, editor) => {
 *         // Handle AI commands
 *         if (command === 'improve') {
 *           const text = editor.state.doc.textContent;
 *           const improved = await improveText(text);
 *           editor.commands.setContent(improved);
 *         }
 *       },
 *     }),
 *   ],
 * });
 * ```
 */
export const SlashCommandExtension = Extension.create<SlashCommandOptions>({
  name: 'slashCommand',

  addOptions() {
    return {
      commands: [],
      onExecute: undefined,
      onAICommand: undefined,
      maxSuggestions: 15, // Increased to show all default commands including AI
    };
  },

  addStorage() {
    return {
      menuElement: null as HTMLElement | null,
    };
  },

  addProseMirrorPlugins() {
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    const extension = this;
    const editor = this.editor;

    // Merge default and custom commands
    const allCommands = [
      ...getDefaultCommands(extension.options.onAICommand),
      ...(extension.options.commands ?? []),
    ];

    return [
      new Plugin<SlashCommandPluginState>({
        key: SLASH_COMMAND_PLUGIN_KEY,

        state: {
          init() {
            return {
              isActive: false,
              query: '',
              position: null,
              selectedIndex: 0,
            };
          },

          apply(tr, value) {
            const meta = tr.getMeta(SLASH_COMMAND_PLUGIN_KEY);
            if (meta) {
              return { ...value, ...meta };
            }

            // Deactivate on document changes that move away from slash
            if (tr.docChanged && value.isActive) {
              const { selection } = tr;
              const $from = selection.$from;

              // Check if we're still in slash command context
              const textBefore = $from.parent.textBetween(
                0,
                $from.parentOffset,
                undefined,
                '\ufffc'
              );
              const slashMatch = textBefore.match(/\/(\w*)$/);

              if (!slashMatch) {
                return {
                  isActive: false,
                  query: '',
                  position: null,
                  selectedIndex: 0,
                };
              }

              return {
                ...value,
                query: slashMatch[1] ?? '',
              };
            }

            return value;
          },
        },

        props: {
          handleTextInput(view, from, _to, text) {
            // Check if typing / at start of line or after space
            if (text === '/') {
              const { state } = view;
              const $from = state.doc.resolve(from);

              // Check if at start of block or after whitespace
              const textBefore = $from.parent.textBetween(
                0,
                $from.parentOffset,
                undefined,
                '\ufffc'
              );
              const isStartOfLine = textBefore.length === 0 || textBefore.endsWith(' ');

              if (isStartOfLine) {
                // Use requestAnimationFrame to ensure we dispatch after the text is inserted
                // and use the view's current state at that time
                requestAnimationFrame(() => {
                  if (view.isDestroyed) return;
                  const currentState = view.state;
                  const tr = currentState.tr.setMeta(SLASH_COMMAND_PLUGIN_KEY, {
                    isActive: true,
                    query: '',
                    position: from + 1, // +1 because the "/" is now inserted
                    selectedIndex: 0,
                  });
                  view.dispatch(tr);
                });
              }
            }

            return false;
          },

          handleKeyDown(view, event) {
            const state = SLASH_COMMAND_PLUGIN_KEY.getState(view.state);
            if (!state?.isActive) {
              return false;
            }

            const filteredCommands = filterCommands(allCommands, state.query).slice(
              0,
              extension.options.maxSuggestions
            );

            // Arrow navigation
            if (event.key === 'ArrowUp') {
              event.preventDefault();
              const newIndex =
                (state.selectedIndex - 1 + filteredCommands.length) % filteredCommands.length;
              const tr = view.state.tr.setMeta(SLASH_COMMAND_PLUGIN_KEY, {
                isActive: state.isActive,
                query: state.query,
                position: state.position,
                selectedIndex: newIndex,
              });
              view.dispatch(tr);
              return true;
            }

            if (event.key === 'ArrowDown') {
              event.preventDefault();
              const newIndex = (state.selectedIndex + 1) % filteredCommands.length;
              const tr = view.state.tr.setMeta(SLASH_COMMAND_PLUGIN_KEY, {
                isActive: state.isActive,
                query: state.query,
                position: state.position,
                selectedIndex: newIndex,
              });
              view.dispatch(tr);
              return true;
            }

            // Enter to select
            if (event.key === 'Enter') {
              event.preventDefault();
              const command = filteredCommands[state.selectedIndex];
              if (command && state.position !== null) {
                // Delete the slash command text (including the /) and close menu in one transaction
                const deleteFrom = state.position - 1; // -1 to include the "/"
                const deleteTo = view.state.selection.from;
                const tr = view.state.tr
                  .delete(deleteFrom, deleteTo)
                  .setMeta(SLASH_COMMAND_PLUGIN_KEY, {
                    isActive: false,
                    query: '',
                    position: null,
                    selectedIndex: 0,
                  });
                view.dispatch(tr);

                // Execute the command after closing menu
                command.execute(editor);
                extension.options.onExecute?.(command);
              }
              return true;
            }

            // Escape to close
            if (event.key === 'Escape') {
              event.preventDefault();
              const tr = view.state.tr.setMeta(SLASH_COMMAND_PLUGIN_KEY, {
                isActive: false,
                query: '',
                position: null,
                selectedIndex: 0,
              });
              view.dispatch(tr);
              return true;
            }

            // Tab to select (like Enter)
            if (event.key === 'Tab') {
              event.preventDefault();
              const command = filteredCommands[state.selectedIndex];
              if (command && state.position !== null) {
                // Delete the slash command text (including the /) and close menu in one transaction
                const deleteFrom = state.position - 1; // -1 to include the "/"
                const deleteTo = view.state.selection.from;
                const tr = view.state.tr
                  .delete(deleteFrom, deleteTo)
                  .setMeta(SLASH_COMMAND_PLUGIN_KEY, {
                    isActive: false,
                    query: '',
                    position: null,
                    selectedIndex: 0,
                  });
                view.dispatch(tr);

                // Execute the command after closing menu
                command.execute(editor);
                extension.options.onExecute?.(command);
              }
              return true;
            }

            return false;
          },

          decorations(editorState) {
            const state = SLASH_COMMAND_PLUGIN_KEY.getState(editorState);

            if (!state?.isActive || state.position === null) {
              // Clean up existing menu
              if (extension.storage.menuElement) {
                extension.storage.menuElement.remove();
                extension.storage.menuElement = null;
              }
              return DecorationSet.empty;
            }

            const filteredCommands = filterCommands(allCommands, state.query).slice(
              0,
              extension.options.maxSuggestions
            );

            // Create or update menu widget with relative wrapper for positioning
            const decoration = Decoration.widget(
              state.position,
              () => {
                // Wrapper with relative position for absolute menu positioning
                const wrapper = document.createElement('span');
                wrapper.className = 'slash-command-wrapper';
                wrapper.style.cssText = 'position: relative; display: inline-block;';

                // onSelect callback to handle menu item click
                const handleSelect = (cmd: SlashCommand) => {
                  const currentState = SLASH_COMMAND_PLUGIN_KEY.getState(editor.state);
                  if (currentState && currentState.position !== null) {
                    // Delete the slash command text and close menu
                    const deleteFrom = currentState.position - 1; // -1 to include the "/"
                    const deleteTo = editor.state.selection.from;
                    const tr = editor.state.tr
                      .delete(deleteFrom, deleteTo)
                      .setMeta(SLASH_COMMAND_PLUGIN_KEY, {
                        isActive: false,
                        query: '',
                        position: null,
                        selectedIndex: 0,
                      });
                    editor.view.dispatch(tr);

                    // Execute command after closing
                    cmd.execute(editor);
                    extension.options.onExecute?.(cmd);
                  }
                };

                const menu = createCommandMenu(
                  filteredCommands,
                  state.selectedIndex,
                  editor,
                  extension.options.onExecute,
                  handleSelect
                );
                wrapper.appendChild(menu);
                extension.storage.menuElement = wrapper;
                return wrapper;
              },
              { side: 1, key: 'slash-command-menu' }
            );

            return DecorationSet.create(editorState.doc, [decoration]);
          },
        },
      }),
    ];
  },

  onDestroy() {
    if (this.storage.menuElement) {
      this.storage.menuElement.remove();
    }
  },
});

/**
 * CSS styles for slash commands (add to your global stylesheet)
 */
export const slashCommandStyles = `
  .slash-command-menu {
    animation: slash-command-fade-in 0.15s ease;
  }

  @keyframes slash-command-fade-in {
    from {
      opacity: 0;
      transform: translateY(-4px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .slash-command-item.is-selected {
    background: var(--accent, #f3f4f6);
  }

  .slash-command-item:focus {
    outline: none;
  }
`;

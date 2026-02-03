/**
 * SlashCommandExtension - Slash commands for quick formatting and AI actions
 *
 * Features:
 * - Trigger on / at start of line
 * - Commands: /heading, /code, /quote, /bullet, /todo, /divider
 * - AI commands: /ai-improve, /ai-summarize, /ai-extract-issues
 * - Keyboard navigation (Arrow keys, Enter, Escape)
 *
 * Command definitions: ./slash-command-items.ts
 * Menu rendering: ./slash-command-menu.ts
 */
import { Extension, type Editor } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import { type SlashCommand, getDefaultCommands, filterCommands } from './slash-command-items';
import { createCommandMenu } from './slash-command-menu';

// Re-export types for consumers
export type { SlashCommand } from './slash-command-items';

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

            const filteredCmds = filterCommands(allCommands, state.query).slice(
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
                  filteredCmds,
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

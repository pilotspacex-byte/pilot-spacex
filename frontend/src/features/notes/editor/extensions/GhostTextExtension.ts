/**
 * GhostTextExtension - AI-powered inline text suggestions
 *
 * Features:
 * - 500ms typing pause trigger for AI suggestions
 * - Faded inline ghost text display after cursor
 * - Tab key = accept full suggestion
 * - Right arrow (at end of line) = accept next word
 * - Escape = dismiss suggestion
 * - SSE connection management for streaming
 * - Visual loading indicator
 */
import { Extension, type Editor } from '@tiptap/core';
import type { Transaction } from '@tiptap/pm/state';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import type { JSONContent } from '@tiptap/core';

// Import slash command plugin key to check if slash command mode is active
const SLASH_COMMAND_PLUGIN_KEY = new PluginKey('slashCommand');

/**
 * Context passed to AI when triggering ghost text
 */
export interface GhostTextContext {
  /** Text before cursor in current document */
  textBeforeCursor: string;
  /** Text after cursor in current block */
  textAfterCursor: string;
  /** Cursor position in document */
  cursorPosition: number;
  /** ID of the current block */
  blockId: string;
  /** Type of current block (paragraph, heading, etc.) */
  blockType: string;
  /** Full document content as JSON */
  document: JSONContent;
}

export interface GhostTextOptions {
  /** Debounce time in ms before triggering AI (default: 500) */
  debounceMs: number;
  /** Minimum characters before triggering suggestions */
  minChars: number;
  /** CSS class for ghost text styling */
  className: string;
  /** Whether ghost text is enabled */
  enabled: boolean;
  /** Callback when AI should be triggered with context */
  onTrigger?: (context: GhostTextContext) => void;
  /** Callback when suggestion is accepted */
  onAccept?: (text: string, acceptType: 'full' | 'word') => void;
  /** Callback when suggestion is dismissed */
  onDismiss?: () => void;
}

interface GhostTextPluginState {
  text: string | null;
  position: number | null;
  isLoading: boolean;
  decorations: DecorationSet;
}

const GHOST_TEXT_PLUGIN_KEY = new PluginKey<GhostTextPluginState>('ghostText');

/**
 * Creates a ghost text decoration widget with Tab hint
 */
function createGhostTextWidget(text: string, className: string): HTMLElement {
  const container = document.createElement('span');
  container.className = `${className}-container`;
  container.setAttribute('data-ghost-text', 'true');
  container.setAttribute('aria-hidden', 'true');
  container.style.cssText = `
    display: inline-flex;
    align-items: baseline;
    gap: 8px;
    pointer-events: none;
    user-select: none;
    animation: ghost-text-fade-in 200ms ease-out;
  `;

  // Ghost text suggestion
  const textSpan = document.createElement('span');
  textSpan.className = className;
  textSpan.textContent = text;
  textSpan.style.cssText = `
    color: var(--ai, hsl(210 40% 55%));
    opacity: 0.5;
    font-style: italic;
    transition: opacity 150ms ease-out;
  `;
  container.appendChild(textSpan);

  // Tab hint badge
  const hint = document.createElement('span');
  hint.className = 'ghost-text-hint';
  hint.style.cssText = `
    display: inline-flex;
    align-items: center;
    gap: 2px;
    padding: 1px 6px;
    font-size: 11px;
    font-weight: 500;
    font-style: normal;
    color: var(--ai, hsl(210 40% 55%));
    background: var(--ai-muted, hsl(210 40% 55% / 0.1));
    border: 1px solid var(--ai-border, hsl(210 40% 55% / 0.2));
    border-radius: 4px;
    opacity: 0.8;
    white-space: nowrap;
    transition: opacity 150ms ease-out;
  `;
  hint.textContent = 'Tab ↹';
  container.appendChild(hint);

  return container;
}

/**
 * Creates an AI-styled loading indicator widget with shimmer effect
 */
function createLoadingWidget(): HTMLElement {
  const container = document.createElement('span');
  container.className = 'ghost-text-loader';
  container.setAttribute('aria-hidden', 'true');
  container.style.cssText = `
    display: inline-flex;
    align-items: center;
    gap: 4px;
    margin-left: 4px;
    padding: 2px 8px;
    background: var(--ai-muted, hsl(210 40% 55% / 0.1));
    border-radius: 4px;
    animation: ghost-text-fade-in 200ms ease-out;
  `;

  // AI icon using CSS instead of SVG for safety
  const icon = document.createElement('span');
  icon.className = 'ghost-text-loader-icon';
  icon.textContent = '✦';
  icon.style.cssText = `
    display: inline-flex;
    font-size: 12px;
    color: var(--ai, hsl(210 40% 55%));
    animation: ghost-text-spin 2s linear infinite;
  `;
  container.appendChild(icon);

  // Loading text with shimmer
  const text = document.createElement('span');
  text.className = 'ghost-text-loader-text';
  text.textContent = 'Thinking';
  text.style.cssText = `
    font-size: 11px;
    font-weight: 500;
    color: var(--ai, hsl(210 40% 55%));
    background: linear-gradient(
      90deg,
      var(--ai, hsl(210 40% 55%)) 0%,
      var(--ai-hover, hsl(210 40% 45%)) 50%,
      var(--ai, hsl(210 40% 55%)) 100%
    );
    background-size: 200% 100%;
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: ghost-text-shimmer 1.5s ease-in-out infinite;
  `;
  container.appendChild(text);

  // Animated dots
  const dots = document.createElement('span');
  dots.className = 'ghost-text-dots';
  dots.style.cssText = `
    font-size: 11px;
    font-weight: 500;
    color: var(--ai, hsl(210 40% 55%));
    animation: ghost-text-dots-blink 1s steps(4, end) infinite;
  `;
  dots.textContent = '...';
  container.appendChild(dots);

  return container;
}

/**
 * Extract the next word from a string (including trailing space)
 */
function getNextWord(text: string): string {
  const trimmed = text.trimStart();
  const match = trimmed.match(/^(\S+\s*)/);
  if (match && match[1] !== undefined) {
    return match[1];
  }
  return trimmed || '';
}

/**
 * GhostTextExtension provides AI-powered inline completions
 *
 * @example
 * ```tsx
 * import { GhostTextExtension } from './extensions/GhostTextExtension';
 *
 * const editor = new Editor({
 *   extensions: [
 *     GhostTextExtension.configure({
 *       debounceMs: 500,
 *       onTrigger: async (context) => {
 *         // Start SSE connection for AI suggestions
 *         const sse = new EventSource('/api/ai/ghost-text');
 *         sse.onmessage = (event) => {
 *           editor.commands.setGhostText(event.data);
 *         };
 *       },
 *       onAccept: (text, type) => {
 *         console.log(`Accepted ${type}: ${text}`);
 *       },
 *     }),
 *   ],
 * });
 * ```
 */
export const GhostTextExtension = Extension.create<GhostTextOptions>({
  name: 'ghostText',

  addOptions() {
    return {
      debounceMs: 500,
      minChars: 10,
      className: 'ghost-text-suggestion',
      enabled: true,
      onTrigger: undefined,
      onAccept: undefined,
      onDismiss: undefined,
    };
  },

  addStorage() {
    return {
      text: null as string | null,
      position: null as number | null,
      debounceTimer: null as ReturnType<typeof setTimeout> | null,
      isLoading: false,
    };
  },

  // eslint-disable-next-line @typescript-eslint/ban-ts-comment
  // @ts-ignore TipTap's RawCommands type requires specific signatures
  addCommands() {
    return {
      /**
       * Set ghost text suggestion at current cursor position
       */
      setGhostText:
        (text: string) =>
        ({ editor, tr }: { editor: Editor; tr: Transaction }) => {
          const { from } = tr.selection;
          this.storage.text = text;
          this.storage.position = from;
          this.storage.isLoading = false;

          // Force a state update to trigger decoration re-render
          const meta = { text, position: from, isLoading: false };
          editor.view.dispatch(editor.state.tr.setMeta(GHOST_TEXT_PLUGIN_KEY, meta));

          return true;
        },

      /**
       * Accept the current ghost text suggestion
       */
      acceptGhostText:
        (acceptType: 'full' | 'word' = 'full') =>
        ({
          editor,
          tr,
          dispatch,
        }: {
          editor: Editor;
          tr: Transaction;
          dispatch?: (tr: Transaction) => void;
        }) => {
          const text = this.storage.text as string | null;
          const position = this.storage.position as number | null;

          if (!text || position === null) {
            return false;
          }

          // Determine what text to insert
          const textToInsert = acceptType === 'full' ? text : getNextWord(text);

          if (!textToInsert) {
            return false;
          }

          if (dispatch) {
            // Insert the text
            tr.insertText(textToInsert, position);
            dispatch(tr);

            if (acceptType === 'full') {
              // Clear the suggestion completely
              this.storage.text = null;
              this.storage.position = null;
              editor.view.dispatch(
                editor.state.tr.setMeta(GHOST_TEXT_PLUGIN_KEY, {
                  text: null,
                  position: null,
                  isLoading: false,
                })
              );
            } else {
              // Update remaining text for partial accept
              const remaining = text.slice(textToInsert.length);
              if (remaining) {
                this.storage.text = remaining;
                this.storage.position = position + textToInsert.length;
                editor.view.dispatch(
                  editor.state.tr.setMeta(GHOST_TEXT_PLUGIN_KEY, {
                    text: remaining,
                    position: position + textToInsert.length,
                    isLoading: false,
                  })
                );
              } else {
                this.storage.text = null;
                this.storage.position = null;
                editor.view.dispatch(
                  editor.state.tr.setMeta(GHOST_TEXT_PLUGIN_KEY, {
                    text: null,
                    position: null,
                    isLoading: false,
                  })
                );
              }
            }

            // Trigger callback
            this.options.onAccept?.(textToInsert, acceptType);
          }

          return true;
        },

      /**
       * Dismiss the current ghost text suggestion
       */
      dismissGhostText:
        () =>
        ({ editor }: { editor: Editor }) => {
          if (!this.storage.text && !this.storage.isLoading) {
            return false;
          }

          // Clear debounce timer
          if (this.storage.debounceTimer) {
            clearTimeout(this.storage.debounceTimer);
            this.storage.debounceTimer = null;
          }

          this.storage.text = null;
          this.storage.position = null;
          this.storage.isLoading = false;

          editor.view.dispatch(
            editor.state.tr.setMeta(GHOST_TEXT_PLUGIN_KEY, {
              text: null,
              position: null,
              isLoading: false,
            })
          );

          this.options.onDismiss?.();
          return true;
        },

      /**
       * Set loading state for ghost text
       */
      setGhostTextLoading:
        (isLoading: boolean) =>
        ({ editor, tr }: { editor: Editor; tr: Transaction }) => {
          this.storage.isLoading = isLoading;
          const { from } = tr.selection;

          editor.view.dispatch(
            editor.state.tr.setMeta(GHOST_TEXT_PLUGIN_KEY, {
              text: null,
              position: isLoading ? from : null,
              isLoading,
            })
          );

          return true;
        },
    };
  },

  addKeyboardShortcuts() {
    return {
      // Accept full suggestion with Tab
      Tab: ({ editor }) => {
        if (this.storage.text) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          return (editor.commands as any).acceptGhostText('full');
        }
        return false;
      },

      // Accept next word with Right Arrow (only at end of current text)
      ArrowRight: ({ editor }) => {
        if (!this.storage.text) {
          return false;
        }

        const { selection } = editor.state;
        const $pos = selection.$from;

        // Only trigger if at the end of current text in the block
        const isAtEnd = $pos.pos === $pos.end();
        if (selection.empty && isAtEnd) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          return (editor.commands as any).acceptGhostText('word');
        }
        return false;
      },

      // Dismiss suggestion with Escape
      Escape: ({ editor }) => {
        if (this.storage.text || this.storage.isLoading) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          return (editor.commands as any).dismissGhostText();
        }
        return false;
      },
    };
  },

  addProseMirrorPlugins() {
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    const extension = this;

    return [
      new Plugin<GhostTextPluginState>({
        key: GHOST_TEXT_PLUGIN_KEY,

        state: {
          init: () => ({
            text: null,
            position: null,
            isLoading: false,
            decorations: DecorationSet.empty,
          }),

          apply: (tr, value) => {
            const meta = tr.getMeta(GHOST_TEXT_PLUGIN_KEY);

            if (meta !== undefined) {
              const { text, position, isLoading } = meta;

              // No suggestion and not loading - clear decorations
              if (!text && !isLoading) {
                return {
                  text: null,
                  position: null,
                  isLoading: false,
                  decorations: DecorationSet.empty,
                };
              }

              const decorations: Decoration[] = [];

              // Loading indicator
              if (isLoading && position !== null) {
                decorations.push(Decoration.widget(position, createLoadingWidget, { side: 1 }));
              }

              // Ghost text suggestion
              if (text && position !== null) {
                decorations.push(
                  Decoration.widget(
                    position,
                    () => createGhostTextWidget(text, extension.options.className),
                    { side: 1 }
                  )
                );
              }

              return {
                text,
                position,
                isLoading,
                decorations: DecorationSet.create(tr.doc, decorations),
              };
            }

            // Clear on any document change (user is typing)
            if (tr.docChanged && value.text) {
              extension.storage.text = null;
              extension.storage.position = null;
              return {
                text: null,
                position: null,
                isLoading: value.isLoading,
                decorations: value.isLoading ? value.decorations : DecorationSet.empty,
              };
            }

            // Map decorations through document changes
            return {
              ...value,
              decorations: value.decorations.map(tr.mapping, tr.doc),
            };
          },
        },

        props: {
          decorations(state) {
            return this.getState(state)?.decorations ?? DecorationSet.empty;
          },

          // Handle text input for debounced trigger
          handleTextInput(view) {
            if (!extension.options.enabled || !extension.options.onTrigger) {
              return false;
            }

            // Check if slash command mode is active - skip ghost text if so
            const slashCommandState = SLASH_COMMAND_PLUGIN_KEY.getState(view.state);
            if (slashCommandState?.isActive) {
              // Clear any existing ghost text and timers when slash command is active
              if (extension.storage.debounceTimer) {
                clearTimeout(extension.storage.debounceTimer);
                extension.storage.debounceTimer = null;
              }
              if (extension.storage.text || extension.storage.isLoading) {
                extension.storage.text = null;
                extension.storage.position = null;
                extension.storage.isLoading = false;
                view.dispatch(
                  view.state.tr.setMeta(GHOST_TEXT_PLUGIN_KEY, {
                    text: null,
                    position: null,
                    isLoading: false,
                  })
                );
              }
              return false;
            }

            // Clear existing debounce timer
            if (extension.storage.debounceTimer) {
              clearTimeout(extension.storage.debounceTimer);
            }

            // Clear existing ghost text on input
            if (extension.storage.text) {
              extension.storage.text = null;
              extension.storage.position = null;
              view.dispatch(
                view.state.tr.setMeta(GHOST_TEXT_PLUGIN_KEY, {
                  text: null,
                  position: null,
                  isLoading: false,
                })
              );
            }

            // Set up debounced AI trigger
            extension.storage.debounceTimer = setTimeout(() => {
              const { state } = view;

              // Double-check slash command isn't active (might have been activated during debounce)
              const currentSlashState = SLASH_COMMAND_PLUGIN_KEY.getState(state);
              if (currentSlashState?.isActive) {
                return;
              }

              const { selection, doc } = state;
              const $pos = selection.$from;

              // Build context for AI
              const textBeforeCursor = doc.textBetween(0, $pos.pos, '\n', '\n');
              const blockEnd = Math.min($pos.end(), doc.content.size);
              const textAfterCursor = doc.textBetween($pos.pos, blockEnd, '\n', '\n');

              // Only trigger if we have enough content
              if (textBeforeCursor.length < extension.options.minChars) {
                return;
              }

              // Skip if text ends with slash command pattern (/ at line start or after space)
              const lastLine = textBeforeCursor.split('\n').pop() ?? '';
              if (lastLine.match(/^\s*\/\w*$/) || lastLine.match(/\s\/\w*$/)) {
                return;
              }

              // Get current block info
              const resolvedPos = doc.resolve($pos.pos);
              const depth = resolvedPos.depth > 0 ? resolvedPos.depth : 0;
              const blockNode = depth > 0 ? resolvedPos.node(depth) : doc;
              const blockId =
                (blockNode.attrs?.blockId as string) || `block-${resolvedPos.start(depth)}`;

              const context: GhostTextContext = {
                textBeforeCursor,
                textAfterCursor,
                cursorPosition: $pos.pos,
                blockId,
                blockType: blockNode.type?.name ?? 'doc',
                document: doc.toJSON() as JSONContent,
              };

              // Show loading state
              extension.storage.isLoading = true;
              view.dispatch(
                state.tr.setMeta(GHOST_TEXT_PLUGIN_KEY, {
                  text: null,
                  position: $pos.pos,
                  isLoading: true,
                })
              );

              // Trigger AI callback
              extension.options.onTrigger?.(context);
            }, extension.options.debounceMs);

            return false;
          },
        },
      }),
    ];
  },

  onDestroy() {
    // Clean up debounce timer
    if (this.storage.debounceTimer) {
      clearTimeout(this.storage.debounceTimer);
    }
  },
});

/**
 * CSS styles for ghost text (add to your global stylesheet)
 */
export const ghostTextStyles = `
  .ghost-text-suggestion-container {
    display: inline-flex;
    align-items: baseline;
    gap: 8px;
    pointer-events: none;
    user-select: none;
  }

  .ghost-text-suggestion {
    color: var(--ai, hsl(210 40% 55%));
    opacity: 0.5;
    font-style: italic;
    transition: opacity 150ms ease-out;
  }

  .ghost-text-hint {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    padding: 1px 6px;
    font-size: 11px;
    font-weight: 500;
    font-style: normal;
    color: var(--ai, hsl(210 40% 55%));
    background: var(--ai-muted, hsl(210 40% 55% / 0.1));
    border: 1px solid var(--ai-border, hsl(210 40% 55% / 0.2));
    border-radius: 4px;
    opacity: 0.8;
    white-space: nowrap;
  }

  .ghost-text-loader {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    margin-left: 4px;
    padding: 2px 8px;
    background: var(--ai-muted, hsl(210 40% 55% / 0.1));
    border-radius: 4px;
  }

  .ghost-text-loader-icon {
    display: inline-flex;
    font-size: 12px;
    color: var(--ai, hsl(210 40% 55%));
  }

  .ghost-text-loader-text {
    font-size: 11px;
    font-weight: 500;
    color: var(--ai, hsl(210 40% 55%));
  }

  .ghost-text-dots {
    font-size: 11px;
    font-weight: 500;
    color: var(--ai, hsl(210 40% 55%));
  }

  @keyframes ghost-text-fade-in {
    from { opacity: 0; transform: translateX(-4px); }
    to { opacity: 1; transform: translateX(0); }
  }

  @keyframes ghost-text-spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  @keyframes ghost-text-shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }

  @keyframes ghost-text-dots-blink {
    0% { content: ''; }
    25% { content: '.'; }
    50% { content: '..'; }
    75% { content: '...'; }
    100% { content: ''; }
  }

  @keyframes ghost-text-pulse {
    0%, 100% { opacity: 0.3; }
    50% { opacity: 0.8; }
  }
`;

/**
 * CodeBlockExtension - Enhanced code block with syntax highlighting
 *
 * Features:
 * - Language selector dropdown
 * - Syntax highlighting via lowlight
 * - Copy code button
 * - Optional line numbers
 */
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight';
import { common, createLowlight } from 'lowlight';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import type { Node as ProseMirrorNode } from '@tiptap/pm/model';

export interface CodeBlockOptions {
  /** Default language for new code blocks */
  defaultLanguage: string;
  /** Available languages for selection */
  languages: string[];
  /** Show line numbers */
  lineNumbers: boolean;
  /** Show copy button */
  showCopyButton: boolean;
  /** Callback when language is changed */
  onLanguageChange?: (language: string, pos: number) => void;
  /** Callback when code is copied */
  onCopy?: (code: string) => void;
}

const CODE_BLOCK_UI_PLUGIN_KEY = new PluginKey('codeBlockUI');

/**
 * Supported languages with display names
 */
export const SUPPORTED_LANGUAGES: Record<string, string> = {
  plaintext: 'Plain Text',
  javascript: 'JavaScript',
  typescript: 'TypeScript',
  python: 'Python',
  rust: 'Rust',
  go: 'Go',
  java: 'Java',
  cpp: 'C++',
  c: 'C',
  csharp: 'C#',
  ruby: 'Ruby',
  php: 'PHP',
  swift: 'Swift',
  kotlin: 'Kotlin',
  html: 'HTML',
  css: 'CSS',
  scss: 'SCSS',
  json: 'JSON',
  yaml: 'YAML',
  markdown: 'Markdown',
  bash: 'Bash',
  shell: 'Shell',
  sql: 'SQL',
  graphql: 'GraphQL',
  dockerfile: 'Dockerfile',
};

/**
 * Create the lowlight instance with common languages
 */
const lowlight = createLowlight(common);

/**
 * Creates language selector element
 */
function createLanguageSelector(
  currentLanguage: string,
  languages: string[],
  pos: number,
  onLanguageChange?: (language: string, pos: number) => void
): HTMLElement {
  const container = document.createElement('div');
  container.className = 'code-block-language-selector';
  container.style.cssText = `
    position: absolute;
    top: 8px;
    left: 8px;
    z-index: 10;
  `;

  const select = document.createElement('select');
  select.className = 'code-block-language-select';
  select.setAttribute('aria-label', 'Select language');
  select.style.cssText = `
    padding: 4px 8px;
    font-size: 12px;
    border-radius: 4px;
    border: 1px solid var(--border, #e5e7eb);
    background: var(--background, white);
    color: var(--foreground, #111827);
    cursor: pointer;
    outline: none;
  `;

  // Add language options
  languages.forEach((lang) => {
    const option = document.createElement('option');
    option.value = lang;
    option.textContent = SUPPORTED_LANGUAGES[lang] ?? lang;
    option.selected = lang === currentLanguage;
    select.appendChild(option);
  });

  select.addEventListener('change', (e) => {
    const target = e.target as HTMLSelectElement;
    onLanguageChange?.(target.value, pos);
  });

  container.appendChild(select);
  return container;
}

/**
 * Creates copy button element
 */
function createCopyButton(code: string, onCopy?: (code: string) => void): HTMLElement {
  const button = document.createElement('button');
  button.className = 'code-block-copy-button';
  button.setAttribute('aria-label', 'Copy code');
  button.setAttribute('type', 'button');
  button.style.cssText = `
    position: absolute;
    top: 8px;
    right: 8px;
    padding: 6px 10px;
    font-size: 12px;
    border-radius: 4px;
    border: 1px solid var(--border, #e5e7eb);
    background: var(--background, white);
    color: var(--muted-foreground, #6b7280);
    cursor: pointer;
    transition: all 0.15s ease;
    z-index: 10;
    display: flex;
    align-items: center;
    gap: 4px;
  `;

  // Copy icon (simple SVG)
  const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  icon.setAttribute('width', '14');
  icon.setAttribute('height', '14');
  icon.setAttribute('viewBox', '0 0 24 24');
  icon.setAttribute('fill', 'none');
  icon.setAttribute('stroke', 'currentColor');
  icon.setAttribute('stroke-width', '2');
  icon.setAttribute('stroke-linecap', 'round');
  icon.setAttribute('stroke-linejoin', 'round');

  const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
  rect.setAttribute('x', '9');
  rect.setAttribute('y', '9');
  rect.setAttribute('width', '13');
  rect.setAttribute('height', '13');
  rect.setAttribute('rx', '2');
  rect.setAttribute('ry', '2');

  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', 'M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1');

  icon.appendChild(rect);
  icon.appendChild(path);

  const text = document.createElement('span');
  text.textContent = 'Copy';

  button.appendChild(icon);
  button.appendChild(text);

  // Hover effect
  button.addEventListener('mouseenter', () => {
    button.style.backgroundColor = 'var(--accent, #f3f4f6)';
    button.style.color = 'var(--foreground, #111827)';
  });
  button.addEventListener('mouseleave', () => {
    button.style.backgroundColor = 'var(--background, white)';
    button.style.color = 'var(--muted-foreground, #6b7280)';
  });

  // Click handler
  button.addEventListener('click', async (e) => {
    e.preventDefault();
    e.stopPropagation();

    try {
      await navigator.clipboard.writeText(code);

      // Show success feedback
      text.textContent = 'Copied!';
      button.style.color = 'var(--success, #10b981)';

      setTimeout(() => {
        text.textContent = 'Copy';
        button.style.color = 'var(--muted-foreground, #6b7280)';
      }, 2000);

      onCopy?.(code);
    } catch (_err) {
      text.textContent = 'Failed';
      setTimeout(() => {
        text.textContent = 'Copy';
      }, 2000);
    }
  });

  return button;
}

/**
 * Creates line numbers element
 */
function createLineNumbers(lineCount: number): HTMLElement {
  const container = document.createElement('div');
  container.className = 'code-block-line-numbers';
  container.setAttribute('aria-hidden', 'true');
  container.style.cssText = `
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 40px;
    padding: 16px 0;
    text-align: right;
    user-select: none;
    font-family: var(--font-mono, monospace);
    font-size: 13px;
    line-height: 1.5;
    color: var(--muted-foreground, #6b7280);
    background: var(--muted, #f9fafb);
    border-right: 1px solid var(--border, #e5e7eb);
  `;

  for (let i = 1; i <= lineCount; i++) {
    const lineNumber = document.createElement('div');
    lineNumber.textContent = String(i);
    lineNumber.style.paddingRight = '8px';
    container.appendChild(lineNumber);
  }

  return container;
}

/**
 * CodeBlockExtension with enhanced UI
 *
 * @example
 * ```tsx
 * import { CodeBlockExtension } from './extensions/CodeBlockExtension';
 *
 * const editor = new Editor({
 *   extensions: [
 *     CodeBlockExtension.configure({
 *       defaultLanguage: 'typescript',
 *       lineNumbers: true,
 *       showCopyButton: true,
 *       onLanguageChange: (lang, pos) => {
 *         editor.commands.updateAttributes('codeBlock', { language: lang });
 *       },
 *     }),
 *   ],
 * });
 * ```
 */
export const CodeBlockExtension = CodeBlockLowlight.extend<CodeBlockOptions>({
  addOptions() {
    return {
      ...this.parent?.(),
      lowlight,
      defaultLanguage: 'plaintext',
      languages: Object.keys(SUPPORTED_LANGUAGES),
      lineNumbers: false,
      showCopyButton: true,
      onLanguageChange: undefined,
      onCopy: undefined,
    };
  },

  addProseMirrorPlugins() {
    const parentPlugins = this.parent?.() ?? [];
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    const extension = this;

    return [
      ...parentPlugins,
      new Plugin({
        key: CODE_BLOCK_UI_PLUGIN_KEY,

        props: {
          decorations(state) {
            const decorations: Decoration[] = [];

            state.doc.descendants((node: ProseMirrorNode, pos: number) => {
              if (node.type.name !== 'codeBlock') {
                return true;
              }

              const language = (node.attrs.language as string) || extension.options.defaultLanguage;
              const code = node.textContent;
              const lineCount = code.split('\n').length;

              // Add wrapper decoration for positioning
              decorations.push(
                Decoration.node(pos, pos + node.nodeSize, {
                  class: 'code-block-wrapper',
                  style: `position: relative; ${extension.options.lineNumbers ? 'padding-left: 48px;' : ''}`,
                })
              );

              // Language selector widget
              decorations.push(
                Decoration.widget(
                  pos + 1,
                  () =>
                    createLanguageSelector(
                      language,
                      extension.options.languages,
                      pos,
                      extension.options.onLanguageChange
                    ),
                  { side: -1, key: `lang-selector-${pos}` }
                )
              );

              // Copy button widget
              if (extension.options.showCopyButton) {
                decorations.push(
                  Decoration.widget(
                    pos + 1,
                    () => createCopyButton(code, extension.options.onCopy),
                    { side: -1, key: `copy-btn-${pos}` }
                  )
                );
              }

              // Line numbers widget
              if (extension.options.lineNumbers) {
                decorations.push(
                  Decoration.widget(pos + 1, () => createLineNumbers(lineCount), {
                    side: -1,
                    key: `line-nums-${pos}`,
                  })
                );
              }

              return false;
            });

            return DecorationSet.create(state.doc, decorations);
          },
        },
      }),
    ];
  },

  addKeyboardShortcuts() {
    return {
      ...this.parent?.(),
      // Exit code block with triple Enter at end
      Enter: ({ editor }) => {
        const { state } = editor;
        const { selection } = state;
        const { $from } = selection;

        if ($from.parent.type.name !== 'codeBlock') {
          return false;
        }

        // Check if cursor is at the end of the code block
        const isAtEnd = $from.parentOffset === $from.parent.content.size;
        const endsWithDoubleNewline = $from.parent.textContent.endsWith('\n\n');

        if (isAtEnd && endsWithDoubleNewline) {
          // Delete the trailing newlines and exit the code block
          return editor
            .chain()
            .command(({ tr }: { tr: import('@tiptap/pm/state').Transaction }) => {
              tr.delete($from.pos - 2, $from.pos);
              return true;
            })
            .exitCode()
            .run();
        }

        return false;
      },
    };
  },
});

// Re-export the lowlight instance for external configuration
export { lowlight };

/**
 * CSS styles for code block (add to your global stylesheet)
 */
export const codeBlockStyles = `
  .code-block-wrapper {
    margin: 16px 0;
    border-radius: 8px;
    overflow: hidden;
  }

  .code-block-wrapper pre {
    margin: 0;
    padding: 40px 16px 16px;
    overflow-x: auto;
    background: var(--muted, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
  }

  .code-block-wrapper code {
    font-family: var(--font-mono, 'JetBrains Mono', monospace);
    font-size: 14px;
    line-height: 1.5;
  }

  .code-block-language-selector {
    opacity: 0;
    transition: opacity 0.15s ease;
  }

  .code-block-copy-button {
    opacity: 0;
    transition: opacity 0.15s ease;
  }

  .code-block-wrapper:hover .code-block-language-selector,
  .code-block-wrapper:hover .code-block-copy-button {
    opacity: 1;
  }

  .code-block-language-select:focus {
    outline: 2px solid var(--ring, #3b82f6);
    outline-offset: 2px;
  }
`;

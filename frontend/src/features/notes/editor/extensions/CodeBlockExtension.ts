/**
 * CodeBlockExtension - Enhanced code block with syntax highlighting
 *
 * Features:
 * - Language selector dropdown
 * - Syntax highlighting via lowlight
 * - Copy code button
 * - Optional line numbers
 * - Mermaid diagram preview (FR-004): unified NodeView with preview/code toggle
 */
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight';
import { common, createLowlight } from 'lowlight';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import type { Node as ProseMirrorNode } from '@tiptap/pm/model';
import { createMermaidNodeView } from './MermaidNodeView';

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
  mermaid: 'Mermaid',
};

/**
 * Create the lowlight instance with common languages
 */
const lowlight = createLowlight(common);

/**
 * Custom highlight.js language definition for Mermaid diagrams.
 * Covers: diagram types, direction keywords, arrows, comments, strings,
 * subgraph/end blocks, participant/actor labels, and style directives.
 */
function hljsMermaid(hljs: Parameters<import('highlight.js').LanguageFn>[0]) {
  return {
    name: 'Mermaid',
    case_insensitive: false,
    keywords: {
      keyword: [
        'graph',
        'flowchart',
        'sequenceDiagram',
        'classDiagram',
        'stateDiagram',
        'stateDiagram-v2',
        'erDiagram',
        'gantt',
        'pie',
        'mindmap',
        'gitGraph',
        'C4Context',
        'C4Container',
        'C4Component',
        'C4Deployment',
        'journey',
        'requirementDiagram',
        'subgraph',
        'end',
      ],
      built_in: [
        'participant',
        'actor',
        'Note',
        'note',
        'loop',
        'alt',
        'else',
        'opt',
        'par',
        'and',
        'critical',
        'break',
        'rect',
        'activate',
        'deactivate',
        'destroy',
        'title',
        'section',
        'dateFormat',
        'axisFormat',
        'class',
        'style',
        'linkStyle',
        'classDef',
        'click',
        'callback',
        'direction',
      ],
      literal: [
        'TD',
        'TB',
        'BT',
        'LR',
        'RL',
        'left of',
        'right of',
        'over',
        'open',
        'closed',
        'active',
        'done',
        'crit',
        'milestone',
      ],
    },
    contains: [
      hljs.QUOTE_STRING_MODE,
      hljs.APOS_STRING_MODE,
      {
        className: 'comment',
        begin: '%%',
        end: '$',
        relevance: 10,
      },
      {
        className: 'operator',
        begin: /-->>|--?>[>|x]?|<--?|===>?|-.->?|-\.-|[|>{}[\]()]/,
        relevance: 0,
      },
      {
        className: 'symbol',
        begin: /:::|---/,
        relevance: 0,
      },
      {
        className: 'number',
        begin: /\b\d{4}-\d{2}-\d{2}\b/,
        relevance: 5,
      },
      {
        className: 'type',
        begin: /\b[A-Z][a-zA-Z0-9_]*\b/,
        relevance: 0,
      },
    ],
  };
}

lowlight.register({ mermaid: hljsMermaid });

/**
 * Creates language selector element
 */
function createLanguageSelector(
  currentLanguage: string,
  languages: string[],
  pos: number,
  onLanguageChange?: (language: string, pos: number) => void
): HTMLElement {
  const ac = new AbortController();
  const container = document.createElement('div');
  container.className = 'code-block-language-selector';
  (container as HTMLElement & { _abort?: AbortController })._abort = ac;
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

  languages.forEach((lang) => {
    const option = document.createElement('option');
    option.value = lang;
    option.textContent = SUPPORTED_LANGUAGES[lang] ?? lang;
    option.selected = lang === currentLanguage;
    select.appendChild(option);
  });

  select.addEventListener(
    'change',
    (e) => {
      const target = e.target as HTMLSelectElement;
      onLanguageChange?.(target.value, pos);
    },
    { signal: ac.signal }
  );

  container.appendChild(select);
  return container;
}

/**
 * Creates copy button element
 */
function createCopyButton(code: string, onCopy?: (code: string) => void): HTMLElement {
  const ac = new AbortController();
  const button = document.createElement('button');
  button.className = 'code-block-copy-button';
  button.setAttribute('aria-label', 'Copy code');
  button.setAttribute('type', 'button');
  (button as HTMLElement & { _abort?: AbortController })._abort = ac;
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

  const sig = { signal: ac.signal };

  button.addEventListener(
    'mouseenter',
    () => {
      button.style.backgroundColor = 'var(--accent, #f3f4f6)';
      button.style.color = 'var(--foreground, #111827)';
    },
    sig
  );
  button.addEventListener(
    'mouseleave',
    () => {
      button.style.backgroundColor = 'var(--background, white)';
      button.style.color = 'var(--muted-foreground, #6b7280)';
    },
    sig
  );

  button.addEventListener(
    'click',
    async (e) => {
      e.preventDefault();
      e.stopPropagation();

      try {
        await navigator.clipboard.writeText(code);
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
    },
    sig
  );

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
 * ProseMirror widget `destroy` callback. Aborts all event listeners
 * registered via AbortController on the widget's DOM node.
 */
function abortWidgetListeners(node: Node) {
  const el = node as HTMLElement & { _abort?: AbortController };
  el._abort?.abort();
}

/**
 * CodeBlockExtension with enhanced UI and mermaid diagram preview.
 *
 * Mermaid blocks use a custom NodeView (MermaidNodeView) that renders a
 * single unified card with preview/code toggle. Non-mermaid blocks use
 * the standard lowlight NodeView with decoration-based UI widgets.
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

  addNodeView() {
    const parentNodeView = this.parent?.();
    return (props) => {
      // Mermaid blocks: use unified NodeView with preview/code toggle
      if ((props.node.attrs.language as string) === 'mermaid') {
        return createMermaidNodeView({
          node: props.node,
          view: props.editor.view,
          getPos: props.getPos,
        });
      }
      // Non-mermaid: delegate to parent (lowlight syntax highlighting)
      if (parentNodeView) {
        return parentNodeView(props);
      }
      // Fallback: plain <pre><code>
      const pre = document.createElement('pre');
      const code = document.createElement('code');
      pre.appendChild(code);
      return { dom: pre, contentDOM: code };
    };
  },

  addProseMirrorPlugins() {
    const parentPlugins = this.parent?.() ?? [];
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    const extension = this;

    /** Build decorations for non-mermaid code blocks only. */
    function buildDecorations(doc: ProseMirrorNode): DecorationSet {
      const decorations: Decoration[] = [];

      doc.descendants((node: ProseMirrorNode, pos: number) => {
        if (node.type.name !== 'codeBlock') return true;

        const language = (node.attrs.language as string) || extension.options.defaultLanguage;
        // Mermaid blocks are handled by MermaidNodeView — skip decorations
        if (language === 'mermaid') return false;

        const code = node.textContent;
        const lineCount = code.split('\n').length;

        // Wrapper decoration for positioning
        decorations.push(
          Decoration.node(pos, pos + node.nodeSize, {
            class: 'code-block-wrapper',
            style: `position: relative; ${extension.options.lineNumbers ? 'padding-left: 48px;' : ''}`,
          })
        );

        // Language selector
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
            { side: -1, key: `lang-selector-${pos}`, destroy: abortWidgetListeners }
          )
        );

        // Copy button
        if (extension.options.showCopyButton) {
          decorations.push(
            Decoration.widget(pos + 1, () => createCopyButton(code, extension.options.onCopy), {
              side: -1,
              key: `copy-btn-${pos}`,
              destroy: abortWidgetListeners,
            })
          );
        }

        // Line numbers
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

      return DecorationSet.create(doc, decorations);
    }

    return [
      ...parentPlugins,
      new Plugin({
        key: CODE_BLOCK_UI_PLUGIN_KEY,

        state: {
          init(_, state): DecorationSet {
            return buildDecorations(state.doc);
          },

          apply(tr, decorationSet, _oldState, newState): DecorationSet {
            if (!tr.docChanged) {
              return decorationSet.map(tr.mapping, tr.doc);
            }
            return buildDecorations(newState.doc);
          },
        },

        props: {
          decorations(state) {
            return CODE_BLOCK_UI_PLUGIN_KEY.getState(state) as DecorationSet | undefined;
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

        const isAtEnd = $from.parentOffset === $from.parent.content.size;
        const endsWithDoubleNewline = $from.parent.textContent.endsWith('\n\n');

        if (isAtEnd && endsWithDoubleNewline) {
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

/**
 * IssueLinkExtension - Auto-detect and link issue identifiers in text
 *
 * Features:
 * - Auto-detect {PROJECT}-{NUMBER} pattern (e.g., PROJ-123)
 * - Styled link with hover preview
 * - Click opens issue in side panel
 * - Typeahead on # or project identifier
 */
import { Extension, type Editor } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import type { Node as ProseMirrorNode } from '@tiptap/pm/model';

/**
 * Issue preview data for hover card
 */
export interface IssuePreview {
  id: string;
  identifier: string;
  title: string;
  state: string;
  priority: string;
  assignee?: {
    name: string;
    avatarUrl?: string;
  };
}

/**
 * Issue link match in document
 */
export interface IssueLinkMatch {
  text: string;
  project: string;
  number: number;
  from: number;
  to: number;
}

export interface IssueLinkOptions {
  /** Pattern for issue identifiers (default: /[A-Z]+-\d+/) */
  pattern: RegExp;
  /** CSS class for issue links */
  className: string;
  /** Callback to fetch issue preview data */
  onHover?: (issueId: string) => Promise<IssuePreview | null>;
  /** Callback when issue link is clicked */
  onClick?: (issueId: string) => void;
  /** Known project prefixes for faster matching */
  projectPrefixes?: string[];
}

interface IssueLinkPluginState {
  decorations: DecorationSet;
}

const ISSUE_LINK_PLUGIN_KEY = new PluginKey<IssueLinkPluginState>('issueLink');

/**
 * Default issue identifier pattern
 * Matches: ABC-123, PROJ-1, MYPROJECT-99999
 */
const DEFAULT_ISSUE_PATTERN = /\b([A-Z][A-Z0-9]*)-(\d+)\b/g;

/**
 * Safe string accessor
 */
function safeString(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

/**
 * State colors for issue links
 */
const STATE_COLORS: Record<string, string> = {
  backlog: '#6b7280',
  todo: '#3b82f6',
  in_progress: '#f59e0b',
  in_review: '#8b5cf6',
  done: '#10b981',
  cancelled: '#ef4444',
};

/**
 * Creates an issue link element with hover preview support
 */
function createIssueLinkElement(
  match: IssueLinkMatch,
  options: IssueLinkOptions,
  _editor: Editor
): HTMLElement {
  const link = document.createElement('span');
  link.className = `issue-link ${options.className}`;
  link.textContent = match.text;
  link.setAttribute('data-issue-id', match.text);
  link.setAttribute('data-project', match.project);
  link.setAttribute('data-number', String(match.number));
  link.setAttribute('role', 'link');
  link.setAttribute('tabindex', '0');

  link.style.cssText = `
    color: var(--primary, #3b82f6);
    background-color: var(--primary-foreground, rgba(59, 130, 246, 0.1));
    padding: 1px 4px;
    border-radius: 4px;
    cursor: pointer;
    font-family: var(--font-mono, monospace);
    font-size: 0.9em;
    transition: background-color 0.15s ease;
  `;

  // Click handler
  if (options.onClick) {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      options.onClick?.(match.text);
    });

    link.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        options.onClick?.(match.text);
      }
    });
  }

  // Hover preview
  if (options.onHover) {
    let hoverTimeout: ReturnType<typeof setTimeout> | null = null;
    let previewElement: HTMLElement | null = null;

    link.addEventListener('mouseenter', () => {
      hoverTimeout = setTimeout(async () => {
        const preview = await options.onHover?.(match.text);
        if (preview && link.parentElement) {
          previewElement = createPreviewCard(preview);
          positionPreviewCard(previewElement, link);
          document.body.appendChild(previewElement);
        }
      }, 300);
    });

    link.addEventListener('mouseleave', () => {
      if (hoverTimeout) {
        clearTimeout(hoverTimeout);
        hoverTimeout = null;
      }
      if (previewElement) {
        previewElement.remove();
        previewElement = null;
      }
    });
  }

  // Hover styling
  link.addEventListener('mouseenter', () => {
    link.style.backgroundColor = 'var(--primary-foreground-hover, rgba(59, 130, 246, 0.2))';
  });
  link.addEventListener('mouseleave', () => {
    link.style.backgroundColor = 'var(--primary-foreground, rgba(59, 130, 246, 0.1))';
  });

  return link;
}

/**
 * Creates a preview card for issue hover
 */
function createPreviewCard(preview: IssuePreview): HTMLElement {
  const card = document.createElement('div');
  card.className = 'issue-preview-card';
  card.setAttribute('role', 'tooltip');

  const stateColor = STATE_COLORS[preview.state] ?? STATE_COLORS.backlog;

  card.style.cssText = `
    position: fixed;
    z-index: 9999;
    background: var(--popover, white);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    padding: 12px;
    max-width: 320px;
    font-size: 14px;
  `;

  // Header with identifier and state
  const header = document.createElement('div');
  header.style.cssText = 'display: flex; align-items: center; gap: 8px; margin-bottom: 8px;';

  const identifier = document.createElement('span');
  identifier.textContent = preview.identifier;
  identifier.style.cssText = `
    font-family: var(--font-mono, monospace);
    font-weight: 600;
    color: var(--foreground, #111827);
  `;

  const state = document.createElement('span');
  state.textContent = preview.state.replace(/_/g, ' ');
  state.style.cssText = `
    font-size: 12px;
    padding: 2px 6px;
    border-radius: 4px;
    background-color: ${stateColor}20;
    color: ${stateColor};
    text-transform: capitalize;
  `;

  header.appendChild(identifier);
  header.appendChild(state);

  // Title
  const title = document.createElement('div');
  title.textContent = preview.title;
  title.style.cssText = `
    color: var(--foreground, #111827);
    line-height: 1.4;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  `;

  card.appendChild(header);
  card.appendChild(title);

  // Assignee (if present)
  if (preview.assignee) {
    const assignee = document.createElement('div');
    assignee.style.cssText = `
      display: flex;
      align-items: center;
      gap: 6px;
      margin-top: 8px;
      font-size: 12px;
      color: var(--muted-foreground, #6b7280);
    `;

    if (preview.assignee.avatarUrl) {
      const avatar = document.createElement('img');
      avatar.src = preview.assignee.avatarUrl;
      avatar.alt = preview.assignee.name;
      avatar.style.cssText = 'width: 20px; height: 20px; border-radius: 50%;';
      assignee.appendChild(avatar);
    }

    const name = document.createElement('span');
    name.textContent = preview.assignee.name;
    assignee.appendChild(name);

    card.appendChild(assignee);
  }

  return card;
}

/**
 * Positions the preview card relative to the link element
 */
function positionPreviewCard(card: HTMLElement, link: HTMLElement): void {
  const rect = link.getBoundingClientRect();
  const cardWidth = 320;

  // Position below the link, centered
  let left = rect.left + rect.width / 2 - cardWidth / 2;
  const top = rect.bottom + 8;

  // Keep within viewport
  if (left < 8) left = 8;
  if (left + cardWidth > window.innerWidth - 8) {
    left = window.innerWidth - cardWidth - 8;
  }

  card.style.left = `${left}px`;
  card.style.top = `${top}px`;
}

/**
 * Find all issue link matches in the document
 */
function findIssueMatches(doc: ProseMirrorNode, pattern: RegExp): IssueLinkMatch[] {
  const matches: IssueLinkMatch[] = [];

  doc.descendants((node, pos) => {
    if (!node.isText || !node.text) {
      return true;
    }

    // Reset regex lastIndex for global pattern
    pattern.lastIndex = 0;

    let match: RegExpExecArray | null;
    while ((match = pattern.exec(node.text)) !== null) {
      matches.push({
        text: match[0],
        project: safeString(match[1]),
        number: parseInt(safeString(match[2]), 10),
        from: pos + match.index,
        to: pos + match.index + match[0].length,
      });
    }

    return true;
  });

  return matches;
}

/**
 * IssueLinkExtension auto-detects and creates links for issue identifiers
 *
 * @example
 * ```tsx
 * import { IssueLinkExtension } from './extensions/IssueLinkExtension';
 *
 * const editor = new Editor({
 *   extensions: [
 *     IssueLinkExtension.configure({
 *       onClick: (issueId) => {
 *         // Open issue in side panel
 *         openIssuePanel(issueId);
 *       },
 *       onHover: async (issueId) => {
 *         // Fetch issue preview
 *         return await fetchIssuePreview(issueId);
 *       },
 *     }),
 *   ],
 * });
 * ```
 */
export const IssueLinkExtension = Extension.create<IssueLinkOptions>({
  name: 'issueLink',

  addOptions() {
    return {
      pattern: DEFAULT_ISSUE_PATTERN,
      className: '',
      onHover: undefined,
      onClick: undefined,
      projectPrefixes: [],
    };
  },

  addProseMirrorPlugins() {
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    const extension = this;
    const editor = this.editor;

    return [
      new Plugin<IssueLinkPluginState>({
        key: ISSUE_LINK_PLUGIN_KEY,

        state: {
          init(_, state) {
            return {
              decorations: buildIssueDecorations(state.doc, extension.options, editor),
            };
          },

          apply(tr, value, _oldState, newState) {
            // Rebuild decorations on document change
            if (tr.docChanged) {
              return {
                decorations: buildIssueDecorations(newState.doc, extension.options, editor),
              };
            }

            // Map existing decorations
            return {
              decorations: value.decorations.map(tr.mapping, tr.doc),
            };
          },
        },

        props: {
          decorations(state) {
            return this.getState(state)?.decorations ?? DecorationSet.empty;
          },
        },
      }),
    ];
  },
});

/**
 * Build decorations for all issue links
 */
function buildIssueDecorations(
  doc: ProseMirrorNode,
  options: IssueLinkOptions,
  editor: Editor
): DecorationSet {
  // Create a new RegExp to avoid issues with global flag
  const pattern = new RegExp(options.pattern.source, options.pattern.flags);
  const matches = findIssueMatches(doc, pattern);

  if (matches.length === 0) {
    return DecorationSet.empty;
  }

  const decorations = matches.map((match) =>
    Decoration.widget(match.from, () => createIssueLinkElement(match, options, editor), {
      side: 0,
      key: `issue-link-${match.text}-${match.from}`,
      marks: [],
    })
  );

  // Also create inline decorations to hide the original text
  const inlineDecorations = matches.map((match) =>
    Decoration.inline(match.from, match.to, {
      class: 'issue-link-hidden',
      style: 'display: none;',
    })
  );

  return DecorationSet.create(doc, [...decorations, ...inlineDecorations]);
}

/**
 * CSS styles for issue links (add to your global stylesheet)
 */
export const issueLinkStyles = `
  .issue-link {
    display: inline;
  }

  .issue-link:focus {
    outline: 2px solid var(--ring, #3b82f6);
    outline-offset: 1px;
  }

  .issue-link-hidden {
    display: none !important;
  }

  .issue-preview-card {
    animation: issue-preview-fade-in 0.15s ease;
  }

  @keyframes issue-preview-fade-in {
    from {
      opacity: 0;
      transform: translateY(-4px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
`;

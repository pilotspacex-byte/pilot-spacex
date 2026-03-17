/**
 * EntityHighlightExtension - Auto-detect and highlight entity names in text
 *
 * Scans document text for exact project name matches (case-insensitive,
 * word boundary). Renders subtle dotted underline decorations with hover
 * tooltips showing project name and link.
 *
 * Follows the IssueLinkExtension decoration pattern:
 * - Different PluginKey to avoid conflicts
 * - Decoration.inline (not widget) — keeps original text visible
 * - `tr.docChanged` guard for performance
 *
 * @see IssueLinkExtension — template for this pattern
 */
import { Extension } from '@tiptap/core';
import type { Node as ProseMirrorNode } from '@tiptap/pm/model';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';

/**
 * Entity match found in document text
 */
export interface EntityMatch {
  name: string;
  projectId: string;
  from: number;
  to: number;
}

export interface EntityHighlightOptions {
  /** CSS class for highlighted entities */
  className: string;
  /** Callback when entity is hovered */
  onEntityHover?: (entity: EntityMatch) => void;
  /** Callback when entity is clicked */
  onEntityClick?: (entity: EntityMatch) => void;
}

/**
 * H-6: Entities are held in extensionStorage (mutable ref updated via useEffect)
 * rather than in frozen extension options — prevents full editor remount when
 * the projectEntities reference changes in NoteCanvasEditor.
 */
export interface EntityHighlightStorage {
  entities: Array<{ name: string; projectId: string }>;
}

interface EntityHighlightPluginState {
  decorations: DecorationSet;
}

const ENTITY_HIGHLIGHT_PLUGIN_KEY = new PluginKey<EntityHighlightPluginState>('entityHighlight');

// ---------------------------------------------------------------------------
// H-5: Module-level RegExp cache — avoids recompiling on every keystroke
// ---------------------------------------------------------------------------
let cachedPattern: RegExp | null = null;
let cachedEntities: Array<{ name: string; projectId: string }> = [];

// ---------------------------------------------------------------------------
// C-1: Module-level hover state — prevents card accumulation in document.body
// ---------------------------------------------------------------------------
let activeCard: HTMLElement | null = null;
let activeTimeout: ReturnType<typeof setTimeout> | null = null;

// ---------------------------------------------------------------------------
// C-2: Global pointermove guard — hides card when pointer leaves a highlight
//      without triggering a pointerleave event (e.g. same-layout navigation
//      where the editor component is not unmounted between route changes).
// ---------------------------------------------------------------------------
function onDocumentPointerMove(event: PointerEvent): void {
  if (activeCard === null && activeTimeout === null) return;
  const el =
    event.target instanceof Element ? event.target : (event.target as Node | null)?.parentElement;
  if (!el?.closest('.entity-highlight')) {
    hideCard();
  }
}

let documentListenerAttached = false;

function attachDocumentListener(): void {
  if (documentListenerAttached) return;
  document.addEventListener('pointermove', onDocumentPointerMove);
  documentListenerAttached = true;
}

function detachDocumentListener(): void {
  if (!documentListenerAttached) return;
  document.removeEventListener('pointermove', onDocumentPointerMove);
  documentListenerAttached = false;
}

// ---------------------------------------------------------------------------
// @internal — exported only for unit tests (not part of the public API)
// ---------------------------------------------------------------------------
/** @internal */
export function _showCard(entity: EntityMatch, rect: DOMRect): void {
  showCard(entity, rect);
}
/** @internal */
export function _hideCard(): void {
  hideCard();
}
/** @internal */
export function _isDocumentListenerAttached(): boolean {
  return documentListenerAttached;
}

/**
 * Escape special regex characters in a string
 */
function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Build a combined regex pattern for all project names.
 * Returns null if no valid names.
 *
 * M-7: Wrapped in try/catch — lookbehind assertions crash Safari < 16.4.
 *      Falls back to \b-only pattern when the advanced form is unsupported.
 */
function buildEntityPattern(entities: Array<{ name: string; projectId: string }>): RegExp | null {
  const validEntities = entities.filter((e) => e.name.trim().length >= 2);
  if (validEntities.length === 0) return null;

  // Sort by length descending so longer names match first (e.g., "Pilot Space" before "Pilot")
  const sorted = [...validEntities].sort((a, b) => b.name.length - a.name.length);

  // Use adaptive boundaries: \b for names that start/end with word chars,
  // lookahead/lookbehind for names with special chars at edges
  const alternatives = sorted.map((e) => {
    const escaped = escapeRegex(e.name);
    const startsWithWord = /^\w/.test(e.name);
    const endsWithWord = /\w$/.test(e.name);
    const prefix = startsWithWord ? '\\b' : '(?<=\\s|^)';
    const suffix = endsWithWord ? '\\b' : '(?=\\s|$)';
    return `${prefix}${escaped}${suffix}`;
  });

  try {
    return new RegExp(`(${alternatives.join('|')})`, 'gi');
  } catch {
    // Fallback for Safari < 16.4 (no lookbehind support)
    const fallback = sorted.map((e) => `\\b${escapeRegex(e.name)}\\b`).join('|');
    return new RegExp(`(${fallback})`, 'gi');
  }
}

/**
 * H-5: Return a cached RegExp, rebuilding only when the entities reference changes.
 */
function getOrBuildPattern(entities: Array<{ name: string; projectId: string }>): RegExp | null {
  if (entities === cachedEntities && cachedPattern !== null) return cachedPattern;
  cachedEntities = entities;
  cachedPattern = buildEntityPattern(entities);
  return cachedPattern;
}

/**
 * Find all entity matches in the document
 */
export function findEntityMatches(
  doc: ProseMirrorNode,
  entities: Array<{ name: string; projectId: string }>
): EntityMatch[] {
  const pattern = getOrBuildPattern(entities);
  if (!pattern) return [];

  // Build name → projectId lookup (case-insensitive)
  const lookup = new Map<string, string>();
  for (const e of entities) {
    lookup.set(e.name.toLowerCase(), e.projectId);
  }

  const matches: EntityMatch[] = [];

  doc.descendants((node, pos) => {
    if (!node.isText || !node.text) return true;

    pattern.lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = pattern.exec(node.text)) !== null) {
      const matchedText = match[0];
      const projectId = lookup.get(matchedText.toLowerCase());
      if (projectId) {
        matches.push({
          name: matchedText,
          projectId,
          from: pos + match.index,
          to: pos + match.index + matchedText.length,
        });
      }
    }

    return true;
  });

  return matches;
}

/**
 * Create an entity hover preview card
 */
function createEntityPreviewCard(entity: EntityMatch): HTMLElement {
  const card = document.createElement('div');
  card.className = 'entity-preview-card';
  card.setAttribute('role', 'tooltip');

  card.style.cssText = `
    position: fixed;
    z-index: 9999;
    background: var(--popover, white);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    padding: 10px 12px;
    max-width: 240px;
    font-size: 13px;
    animation: entity-preview-fade-in 0.15s ease;
  `;

  const nameEl = document.createElement('div');
  nameEl.textContent = entity.name;
  nameEl.style.cssText = `
    font-weight: 600;
    color: var(--foreground, #111827);
    margin-bottom: 4px;
  `;

  const typeEl = document.createElement('div');
  typeEl.textContent = 'Project';
  typeEl.style.cssText = `
    font-size: 11px;
    color: var(--muted-foreground, #6b7280);
  `;

  card.appendChild(nameEl);
  card.appendChild(typeEl);

  return card;
}

/**
 * Position the preview card relative to a decoration element.
 *
 * L-4: Flip card above the target when there is insufficient space below
 *      the viewport bottom.
 */
function positionEntityPreviewCard(card: HTMLElement, rect: DOMRect): void {
  const cardWidth = 240;
  let left = rect.left + rect.width / 2 - cardWidth / 2;

  if (left < 8) left = 8;
  if (left + cardWidth > window.innerWidth - 8) {
    left = window.innerWidth - cardWidth - 8;
  }

  // Default: position below the target
  card.style.left = `${left}px`;
  card.style.top = `${rect.bottom + window.scrollY + 6}px`;

  // L-4: After the card is in the DOM we can measure its rendered height.
  // getBoundingClientRect() returns zeros for elements not yet in the flow,
  // so we use offsetHeight (available once the element is appended but
  // before the browser paints). The caller appends the card before calling
  // this function, so offsetHeight is already valid.
  const cardHeight = card.offsetHeight;
  const spaceBelow = window.innerHeight - rect.bottom - 6;
  if (cardHeight > spaceBelow && rect.top > cardHeight + 6) {
    card.style.top = `${rect.top + window.scrollY - cardHeight - 6}px`;
  }
}

// ---------------------------------------------------------------------------
// C-1: Centralised show/hide helpers that guarantee at most one card exists
// ---------------------------------------------------------------------------

function showCard(entity: EntityMatch, rect: DOMRect): void {
  if (activeTimeout !== null) {
    clearTimeout(activeTimeout);
    activeTimeout = null;
  }
  activeCard?.remove();
  activeCard = null;

  // C-2: Attach global guard so the card is hidden if the pointer moves off the
  // highlight without firing pointerleave (e.g. same-layout route navigation).
  attachDocumentListener();

  activeTimeout = setTimeout(() => {
    const card = createEntityPreviewCard(entity);
    document.body.appendChild(card);
    // Position after appending so offsetHeight is available (L-4 guard)
    positionEntityPreviewCard(card, rect);
    activeCard = card;
    activeTimeout = null;
  }, 300);
}

function hideCard(): void {
  if (activeTimeout !== null) {
    clearTimeout(activeTimeout);
    activeTimeout = null;
  }
  activeCard?.remove();
  activeCard = null;

  // C-2: Detach the global guard once there is nothing to hide.
  detachDocumentListener();
}

/**
 * Build inline decorations for all entity matches
 */
function buildEntityDecorations(
  doc: ProseMirrorNode,
  entities: Array<{ name: string; projectId: string }>,
  className: string
): DecorationSet {
  const matches = findEntityMatches(doc, entities);
  if (matches.length === 0) return DecorationSet.empty;

  const decorations = matches.map((match) => {
    const attrs: Record<string, string> = {
      class: `entity-highlight ${className}`.trim(),
      style:
        'border-bottom: 1px dotted rgba(41, 163, 134, 0.5); cursor: pointer; transition: border-color 0.15s;',
      'data-entity-project-id': match.projectId,
      'data-entity-name': match.name,
    };

    return Decoration.inline(match.from, match.to, attrs);
  });

  return DecorationSet.create(doc, decorations);
}

/**
 * EntityHighlightExtension auto-detects and highlights project names in note text.
 *
 * @example
 * ```tsx
 * import { EntityHighlightExtension } from './extensions/EntityHighlightExtension';
 *
 * const editor = new Editor({
 *   extensions: [
 *     EntityHighlightExtension.configure({
 *       projectEntities: [
 *         { name: 'Frontend', projectId: 'proj-1' },
 *         { name: 'Backend', projectId: 'proj-2' },
 *       ],
 *       onEntityClick: (entity) => router.push(`/projects/${entity.projectId}`),
 *     }),
 *   ],
 * });
 * ```
 */
export const EntityHighlightExtension = Extension.create<
  EntityHighlightOptions,
  EntityHighlightStorage
>({
  name: 'entityHighlight',

  addOptions() {
    return {
      className: '',
      onEntityHover: undefined,
      onEntityClick: undefined,
    };
  },

  addStorage(): EntityHighlightStorage {
    return { entities: [] };
  },

  addProseMirrorPlugins() {
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    const extension = this;

    function getEntities(): Array<{ name: string; projectId: string }> {
      return (
        (
          (extension.editor?.storage as unknown as Record<string, unknown>)?.['entityHighlight'] as
            | EntityHighlightStorage
            | undefined
        )?.entities ?? []
      );
    }

    return [
      new Plugin<EntityHighlightPluginState>({
        key: ENTITY_HIGHLIGHT_PLUGIN_KEY,

        state: {
          init(_, state) {
            return {
              decorations: buildEntityDecorations(
                state.doc,
                getEntities(),
                extension.options.className
              ),
            };
          },

          apply(tr, value) {
            // Only rebuild decorations when document changes (performance guard)
            if (tr.docChanged) {
              const entities = getEntities();
              if (entities.length === 0) return { decorations: DecorationSet.empty };
              return {
                decorations: buildEntityDecorations(tr.doc, entities, extension.options.className),
              };
            }

            // Map existing decorations through transaction mapping
            return {
              decorations: value.decorations.map(tr.mapping, tr.doc),
            };
          },
        },

        props: {
          decorations(state) {
            return this.getState(state)?.decorations ?? DecorationSet.empty;
          },

          handleDOMEvents: {
            // C-1: mouseover replaced by pointerover; leave handled by pointerleave
            // (pointerleave does not bubble — no false fires from child elements)
            pointerover(_, event) {
              const target = event.target as HTMLElement;
              if (!target.classList?.contains('entity-highlight')) return false;

              const projectId = target.dataset.entityProjectId;
              const name = target.dataset.entityName;
              if (!projectId || !name) return false;

              const rect = target.getBoundingClientRect();
              showCard({ name, projectId, from: 0, to: 0 }, rect);

              // Notify callback
              if (extension.options.onEntityHover) {
                extension.options.onEntityHover({ name, projectId, from: 0, to: 0 });
              }

              return false;
            },

            pointerleave(_, event) {
              const target = event.target as HTMLElement;
              if (!target.classList?.contains('entity-highlight')) return false;
              hideCard();
              return false;
            },

            click(_, event) {
              const target = event.target as HTMLElement;
              if (!target.classList?.contains('entity-highlight')) return false;

              const projectId = target.dataset.entityProjectId;
              const name = target.dataset.entityName;
              if (!projectId || !name) return false;

              if (extension.options.onEntityClick) {
                extension.options.onEntityClick({ name, projectId, from: 0, to: 0 });
              }

              return false;
            },
          },
        },

        // C-1: Cleanup dangling card/timeout when the editor is destroyed
        destroy() {
          hideCard();
        },
      }),
    ];
  },
});

/**
 * CSS styles for entity highlights (add to global stylesheet)
 */
export const entityHighlightStyles = `
  .entity-highlight:hover {
    border-bottom-color: rgba(41, 163, 134, 0.8) !important;
  }

  .entity-preview-card {
    animation: entity-preview-fade-in 0.15s ease;
  }

  @keyframes entity-preview-fade-in {
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

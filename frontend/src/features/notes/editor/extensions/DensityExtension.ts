/**
 * DensityExtension — TipTap extension for block density controls (M8, Feature 016)
 *
 * T-129: `collapsed` boolean attribute on block nodes, collapse/expand toggle
 * T-130: Intent block collapse — "[Intent] {what} — {status}"
 * T-131: Progress block collapse — "[{skill-name}] {status} {summary}"
 * T-132: AI block group summary — consecutive AI blocks grouped + collapsed if >3
 * T-133: Focus Mode — hides all ai:-owned blocks (<200ms toggle)
 * T-134: Collapse persistence — localStorage per noteId
 *
 * FR-095: Intent blocks collapse to single line.
 * FR-096: Progress blocks collapse to single line.
 * FR-098: Focus Mode toggle hides AI blocks.
 * FR-099: Consecutive AI blocks grouped with expand/collapse header.
 */
import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import type { Node as ProseMirrorNode } from '@tiptap/pm/model';

export interface DensityOptions {
  /** Note ID for localStorage persistence (T-134). Empty string disables persistence. */
  noteId: string;
  /**
   * Initial Focus Mode state. When true, all ai:-owned blocks are hidden.
   * Overridden by localStorage if noteId is set.
   */
  focusModeDefault?: boolean;
}

export interface DensityStorage {
  /** Map of blockId -> collapsed state. Persisted to localStorage. */
  collapseState: Map<string, boolean>;
  /** Whether Focus Mode is active (hides all ai: blocks). */
  focusMode: boolean;
}

const DENSITY_PLUGIN_KEY = new PluginKey<DecorationSet>('density');
const ATTR_COLLAPSED = 'collapsed';
const ATTR_BLOCK_ID = 'blockId';
const ATTR_OWNER = 'owner';

/** Block types that support collapse. */
const COLLAPSIBLE_TYPES = [
  'paragraph',
  'heading',
  'bulletList',
  'orderedList',
  'codeBlock',
  'blockquote',
  'pmBlock',
];

function getLocalStorageKey(noteId: string): string {
  return `pilot-density-${noteId}`;
}

function loadCollapseState(noteId: string): Map<string, boolean> {
  if (!noteId || typeof window === 'undefined') return new Map();
  try {
    const raw = localStorage.getItem(getLocalStorageKey(noteId));
    if (!raw) return new Map();
    const obj = JSON.parse(raw) as Record<string, boolean>;
    return new Map(Object.entries(obj));
  } catch {
    return new Map();
  }
}

function saveCollapseState(noteId: string, state: Map<string, boolean>): void {
  if (!noteId || typeof window === 'undefined') return;
  try {
    const obj: Record<string, boolean> = {};
    state.forEach((v, k) => {
      obj[k] = v;
    });
    localStorage.setItem(getLocalStorageKey(noteId), JSON.stringify(obj));
  } catch {
    // localStorage unavailable (SSR / private mode)
  }
}

function loadFocusMode(noteId: string): boolean {
  if (!noteId || typeof window === 'undefined') return false;
  try {
    return localStorage.getItem(`pilot-focusmode-${noteId}`) === 'true';
  } catch {
    return false;
  }
}

function saveFocusMode(noteId: string, active: boolean): void {
  if (!noteId || typeof window === 'undefined') return;
  try {
    localStorage.setItem(`pilot-focusmode-${noteId}`, active ? 'true' : 'false');
  } catch {
    // ignore
  }
}

/** Build single-line summary for a collapsed block. */
export function buildCollapseSummary(node: ProseMirrorNode): string {
  const type = node.type.name;

  // Intent block (pmBlock with blockType="intent")
  if (type === 'pmBlock') {
    const blockType = node.attrs.blockType as string | undefined;
    if (blockType === 'intent') {
      try {
        const data = JSON.parse((node.attrs.data as string) || '{}') as Record<string, string>;
        const what = data.what ?? data.title ?? 'Intent';
        const status = data.status ?? '';
        return status ? `[Intent] ${what} — ${status}` : `[Intent] ${what}`;
      } catch {
        return '[Intent]';
      }
    }
    if (blockType === 'progress') {
      try {
        const data = JSON.parse((node.attrs.data as string) || '{}') as Record<string, string>;
        const skill = data.skillName ?? data.skill_name ?? 'AI';
        const status = data.status ?? '';
        const summary = data.summary ?? '';
        const emoji =
          status === 'done'
            ? '\u2713'
            : status === 'running'
              ? '\u29D7'
              : status === 'failed'
                ? '\u2717'
                : '\u2026';
        return summary ? `[${skill}] ${emoji} ${summary}` : `[${skill}] ${emoji} ${status}`.trim();
      } catch {
        return '[Progress]';
      }
    }
    return `[${(node.attrs.blockType as string) || 'Block'}]`;
  }

  // Default: first 80 chars of text content
  const text = node.textContent.trim();
  const truncated = text.length > 80 ? `${text.slice(0, 80)}\u2026` : text;
  return truncated || `[${type}]`;
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    density: {
      /** Toggle collapsed state for a block by blockId. */
      toggleBlockCollapse: (blockId: string) => ReturnType;
      /** Set collapsed state for a block. */
      setBlockCollapsed: (blockId: string, collapsed: boolean) => ReturnType;
      /** Toggle Focus Mode (hides all ai: blocks). */
      toggleFocusMode: () => ReturnType;
      /** Set Focus Mode explicitly. */
      setFocusMode: (active: boolean) => ReturnType;
      /** Collapse all AI block groups with >3 consecutive blocks. */
      autoCollapseAIGroups: () => ReturnType;
    };
  }
}

export const DensityExtension = Extension.create<DensityOptions, DensityStorage>({
  name: 'density',

  addOptions(): DensityOptions {
    return { noteId: '', focusModeDefault: false };
  },

  addStorage(): DensityStorage {
    return {
      collapseState: new Map(),
      focusMode: false,
    };
  },

  addGlobalAttributes() {
    return [
      {
        types: COLLAPSIBLE_TYPES,
        attributes: {
          [ATTR_COLLAPSED]: {
            default: false,
            parseHTML: (element) => element.getAttribute('data-collapsed') === 'true',
            renderHTML: (attributes) => {
              const collapsed = attributes[ATTR_COLLAPSED] as boolean;
              return collapsed ? { 'data-collapsed': 'true' } : {};
            },
          },
        },
      },
    ];
  },

  addCommands() {
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    const ext = this;

    return {
      toggleBlockCollapse:
        (blockId: string) =>
        ({ commands }) => {
          const current = ext.storage.collapseState.get(blockId) ?? false;
          return commands.setBlockCollapsed(blockId, !current);
        },

      setBlockCollapsed:
        (blockId: string, collapsed: boolean) =>
        ({ tr, state, dispatch }) => {
          let found = false;
          state.doc.descendants((node, pos) => {
            if (found) return false;
            if (!node.isBlock || node.attrs[ATTR_BLOCK_ID] !== blockId) return;
            found = true;
            if (dispatch) {
              tr.setNodeMarkup(pos, undefined, {
                ...node.attrs,
                [ATTR_COLLAPSED]: collapsed,
              });
              tr.setMeta('densityCollapse', true);
              dispatch(tr);
            }
          });
          if (found) {
            ext.storage.collapseState.set(blockId, collapsed);
            saveCollapseState(ext.options.noteId, ext.storage.collapseState);
          }
          return found;
        },

      toggleFocusMode:
        () =>
        ({ dispatch, tr }) => {
          const next = !ext.storage.focusMode;
          ext.storage.focusMode = next;
          saveFocusMode(ext.options.noteId, next);
          // Dispatch an empty tr to trigger decoration re-render
          if (dispatch) dispatch(tr.setMeta('densityFocusMode', next));
          return true;
        },

      setFocusMode:
        (active: boolean) =>
        ({ dispatch, tr }) => {
          ext.storage.focusMode = active;
          saveFocusMode(ext.options.noteId, active);
          if (dispatch) dispatch(tr.setMeta('densityFocusMode', active));
          return true;
        },

      autoCollapseAIGroups:
        () =>
        ({ state, dispatch, tr }) => {
          // Find consecutive AI-owned blocks; collapse groups >3
          let groupStart = -1;
          let groupCount = 0;
          let lastOwner = '';
          let changed = false;

          const collapse = (from: number, to: number) => {
            state.doc.nodesBetween(from, to, (node, pos) => {
              if (!node.isBlock) return;
              const bid = node.attrs[ATTR_BLOCK_ID] as string | undefined;
              if (bid) {
                tr.setNodeMarkup(pos, undefined, {
                  ...node.attrs,
                  [ATTR_COLLAPSED]: true,
                });
                ext.storage.collapseState.set(bid, true);
                changed = true;
              }
            });
          };

          state.doc.forEach((node, offset) => {
            const owner = (node.attrs[ATTR_OWNER] as string | undefined) ?? '';
            const isAI = owner.startsWith('ai:');
            if (isAI && owner === lastOwner) {
              groupCount++;
              if (groupCount === 1) groupStart = offset;
            } else {
              if (groupCount > 3 && groupStart >= 0) {
                collapse(groupStart, offset);
              }
              groupStart = isAI ? offset : -1;
              groupCount = isAI ? 1 : 0;
              lastOwner = owner;
            }
          });

          // Handle trailing group
          if (groupCount > 3 && groupStart >= 0) {
            collapse(groupStart, state.doc.content.size);
          }

          if (changed) {
            tr.setMeta('densityCollapse', true);
            saveCollapseState(this.options.noteId, ext.storage.collapseState);
            if (dispatch) dispatch(tr);
          }
          return changed;
        },
    };
  },

  onCreate() {
    const { editor } = this;
    if (!editor) return;

    // T-134: Restore collapse state from localStorage
    const savedCollapse = loadCollapseState(this.options.noteId);
    this.storage.collapseState = savedCollapse;

    // T-133: Restore focus mode from localStorage
    this.storage.focusMode =
      loadFocusMode(this.options.noteId) || (this.options.focusModeDefault ?? false);

    // T-132: Auto-collapse AI groups >3 blocks on initial load
    editor.commands.autoCollapseAIGroups();
  },

  addProseMirrorPlugins() {
    const { storage } = this;
    // AI-C1: capture editor reference so keydown handler can call commands
    const getEditor = () => this.editor;

    return [
      new Plugin({
        key: DENSITY_PLUGIN_KEY,

        props: {
          // AI-C1: keyboard handler — Enter/Space on a collapsed block expands it
          handleDOMEvents: {
            keydown(_view, event) {
              if (event.key !== 'Enter' && event.key !== ' ') return false;
              const target = event.target as HTMLElement | null;
              if (!target) return false;
              const blockId = target.getAttribute('data-density-block-id');
              if (!blockId) return false;
              event.preventDefault();
              getEditor()?.commands.toggleBlockCollapse(blockId);
              return true;
            },
          },

          // T-133: Focus Mode — hide all ai:-owned blocks via CSS class
          // T-129/T-130/T-131/T-132: Collapse decorations
          decorations(state) {
            const decos: Decoration[] = [];
            const focusMode = storage.focusMode;

            state.doc.descendants((node, pos) => {
              if (!node.isBlock) return;

              const owner = (node.attrs[ATTR_OWNER] as string | undefined) ?? '';
              const isAI = owner.startsWith('ai:');
              const collapsed =
                storage.collapseState.get(node.attrs[ATTR_BLOCK_ID] as string) ??
                (node.attrs[ATTR_COLLAPSED] as boolean | undefined) ??
                false;

              // Focus Mode: add CSS class to hide AI blocks
              if (focusMode && isAI) {
                decos.push(
                  Decoration.node(pos, pos + node.nodeSize, {
                    class: 'density-focus-hidden',
                    'aria-hidden': 'true',
                    inert: '',
                  })
                );
                return;
              }

              // Collapsed state: add summary class
              if (collapsed) {
                const summary = buildCollapseSummary(node);
                const blockId = (node.attrs[ATTR_BLOCK_ID] as string | undefined) ?? '';
                decos.push(
                  Decoration.node(pos, pos + node.nodeSize, {
                    class: 'density-collapsed',
                    'data-summary': summary,
                    // AI-C1: keyboard accessibility for collapsed block
                    tabindex: '0',
                    role: 'button',
                    'aria-label': `Expand block: ${summary}`,
                    'data-density-block-id': blockId,
                  })
                );
              }
            });

            return DecorationSet.create(state.doc, decos);
          },
        },
      }),
    ];
  },
});

export default DensityExtension;

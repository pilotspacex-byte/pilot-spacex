/**
 * LineGutterExtension - VS Code-style line numbers with heading fold/unfold.
 *
 * Line numbers are clickable decoration widgets that highlight the block.
 * Fold widgets are ProseMirror decoration widgets on heading nodes.
 * Collapsed blocks receive `.line-gutter-hidden` class via node decorations.
 * Selected block highlight uses ProseMirror plugin state field (not mutable storage)
 * to guarantee decorations stay in sync.
 *
 * Memory optimization: Uses `state` field with `init`/`apply` instead of
 * `props.decorations(state)`. Decorations are only rebuilt when the document
 * changes or fold/select meta is dispatched — cursor blink, selection, and
 * focus events return the previous DecorationSet (zero allocation).
 *
 * @module features/notes/editor/extensions/LineGutterExtension
 */
import { Extension } from '@tiptap/core';
import type { Editor } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import type { EditorState } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import type { Node as ProseMirrorNode } from '@tiptap/pm/model';
import type { Transaction } from '@tiptap/pm/state';
import { TextSelection } from '@tiptap/pm/state';

export interface LineGutterOptions {
  /** Node types that can be folded (default: ['heading']) */
  foldableTypes: string[];
}

export interface LineGutterStorage {
  /** Block IDs currently collapsed */
  collapsedBlocks: Set<string>;
}

// TipTap command type augmentation
declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    lineGutter: {
      toggleFold: (blockId: string) => ReturnType;
      expandAll: () => ReturnType;
      collapseAll: () => ReturnType;
      selectBlock: (blockId: string) => ReturnType;
    };
  }
}

const LINE_GUTTER_KEY = new PluginKey('lineGutter');

/**
 * Container node types that wrap child content blocks.
 * These get blockIds but should not receive line numbers or count toward line totals
 * because their text content is already counted via their child nodes.
 */
const WRAPPER_NODE_TYPES = new Set([
  'bulletList',
  'orderedList',
  'listItem',
  'taskList',
  'taskItem',
  'blockquote',
  'table',
  'tableRow',
  'tableCell',
  'tableHeader',
  'horizontalRule',
]);

/** Transaction metadata key for setting the selected block */
const SELECT_BLOCK_META = 'lineGutterSelectBlock';

/** Transaction metadata key for signaling fold/expand rebuild */
const LINE_GUTTER_REBUILD = 'lineGutterRebuild';

/** Plugin state: tracks which block is highlighted + decoration set */
interface LineGutterPluginState {
  selectedBlockId: string | null;
  decorations: DecorationSet;
}

/**
 * Given a collapsed heading, returns the set of blockIds that should be hidden.
 * Hides all content between the heading and the next heading of same or higher level.
 */
function computeHiddenBlockIds(doc: ProseMirrorNode, collapsedBlocks: Set<string>): Set<string> {
  const hidden = new Set<string>();
  let hideUntilLevel: number | null = null;

  doc.descendants((node) => {
    const blockId = node.attrs.blockId as string | undefined;

    if (node.type.name === 'heading') {
      const level = node.attrs.level as number;

      if (hideUntilLevel !== null && level <= hideUntilLevel) {
        hideUntilLevel = null;
      }

      if (hideUntilLevel !== null && blockId) {
        hidden.add(blockId);
      }

      if (blockId && collapsedBlocks.has(blockId) && hideUntilLevel === null) {
        hideUntilLevel = level;
      }
    } else {
      if (hideUntilLevel !== null && blockId) {
        hidden.add(blockId);
      }
    }

    return true;
  });

  return hidden;
}

/** Padding values (px) for wrapper types that indent their children. */
const INDENT_PX: Record<string, number> = {
  bulletList: 24, // 1.5rem
  orderedList: 24, // 1.5rem
  blockquote: 16, // 1rem
};

/**
 * Walk ancestor nodes from `pos` upward and sum the CSS padding-left of
 * wrapper ancestors. This offset is used to pull nested line numbers back
 * so they align vertically with top-level line numbers.
 */
function computeNestingOffset(doc: ProseMirrorNode, pos: number): number {
  const $pos = doc.resolve(pos);
  let offset = 0;
  for (let d = $pos.depth; d > 0; d--) {
    const ancestor = $pos.node(d);
    const indent = INDENT_PX[ancestor.type.name];
    if (indent) {
      offset += indent;
    }
  }
  return offset;
}

function createFoldWidget(blockId: string, isCollapsed: boolean, toggle: () => void): HTMLElement {
  const btn = document.createElement('button');
  btn.className = 'line-gutter-fold-widget';
  btn.setAttribute('aria-label', isCollapsed ? 'Expand section' : 'Collapse section');
  btn.setAttribute('data-fold-block', blockId);
  btn.textContent = isCollapsed ? '▸' : '▾';

  btn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    toggle();
  });

  btn.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggle();
    }
  });

  return btn;
}

function createLineNumberWidget(
  lineNum: number,
  blockId: string,
  blockPos: number,
  editorInstance: Editor,
  nestingOffsetPx: number
): HTMLElement {
  const span = document.createElement('span');
  span.className = 'line-gutter-number';
  span.textContent = String(lineNum);
  if (nestingOffsetPx > 0) {
    span.style.left = `${-44 - nestingOffsetPx}px`;
  }
  span.setAttribute('role', 'button');
  span.setAttribute('tabindex', '-1');
  span.setAttribute('aria-label', `Select line ${lineNum}`);
  span.setAttribute('data-line-block', blockId);

  // mousedown on the widget element itself — stopPropagation prevents
  // the event from reaching view.dom, so ProseMirror's internal
  // mousedown handler never fires and can't override our selection.
  span.addEventListener('mousedown', (e) => {
    e.preventDefault();
    e.stopPropagation();

    const view = editorInstance.view;
    const state = view.state;

    // Place cursor at start of block + set selected block via transaction meta
    const cursorPos = blockPos + 1;
    const tr = state.tr.setSelection(TextSelection.create(state.doc, cursorPos));
    tr.setMeta(SELECT_BLOCK_META, blockId);
    view.dispatch(tr);
    view.focus();
  });

  return span;
}

/**
 * Build a full DecorationSet for line numbers, fold widgets, selected block
 * highlight, and hidden blocks.
 */
function buildGutterDecorations(
  state: EditorState,
  selectedBlockId: string | null,
  storage: LineGutterStorage,
  options: LineGutterOptions,
  editor: Editor
): DecorationSet {
  const hiddenBlocks = computeHiddenBlockIds(state.doc, storage.collapsedBlocks);
  const decorations: Decoration[] = [];
  let lineNum = 0;

  state.doc.descendants((node, pos) => {
    const blockId = node.attrs.blockId as string | undefined;
    if (!blockId) return true;

    const isWrapper = WRAPPER_NODE_TYPES.has(node.type.name);

    if (!isWrapper) {
      const text = node.textContent;
      const blockLines = text ? (text.match(/\n/g)?.length ?? 0) + 1 : 1;
      const blockStartLine = lineNum + 1;
      lineNum += blockLines;

      const contentPos = pos + 1;
      const nestingOffset = computeNestingOffset(state.doc, pos);
      const numWidget = createLineNumberWidget(blockStartLine, blockId, pos, editor, nestingOffset);

      decorations.push(
        Decoration.widget(contentPos, numWidget, {
          side: -1,
          key: `num-${blockId}`,
        })
      );

      if (options.foldableTypes.includes(node.type.name)) {
        const isCollapsed = storage.collapsedBlocks.has(blockId);

        const widget = createFoldWidget(blockId, isCollapsed, () => {
          editor.commands.toggleFold(blockId);
        });

        decorations.push(
          Decoration.widget(contentPos, widget, {
            side: -1,
            key: `fold-${blockId}`,
          })
        );
      }
    }

    if (selectedBlockId === blockId) {
      decorations.push(
        Decoration.node(pos, pos + node.nodeSize, {
          class: 'line-gutter-selected',
        })
      );
    }

    if (hiddenBlocks.has(blockId)) {
      decorations.push(
        Decoration.node(pos, pos + node.nodeSize, {
          class: 'line-gutter-hidden',
        })
      );
    }

    return true;
  });

  return DecorationSet.create(state.doc, decorations);
}

export const LineGutterExtension = Extension.create<LineGutterOptions, LineGutterStorage>({
  name: 'lineGutter',

  addOptions() {
    return {
      foldableTypes: ['heading'],
    };
  },

  addStorage(): LineGutterStorage {
    return {
      collapsedBlocks: new Set<string>(),
    };
  },

  addCommands() {
    return {
      toggleFold:
        (blockId: string) =>
        ({
          dispatch,
          state,
        }: {
          dispatch: ((tr: Transaction) => void) | undefined;
          state: EditorState;
        }) => {
          if (!dispatch) return false;
          const typedStorage = this.storage as LineGutterStorage;

          if (typedStorage.collapsedBlocks.has(blockId)) {
            typedStorage.collapsedBlocks.delete(blockId);
          } else {
            typedStorage.collapsedBlocks.add(blockId);
          }

          const tr = state.tr;
          tr.setMeta(LINE_GUTTER_REBUILD, true);
          dispatch(tr);
          return true;
        },

      expandAll:
        () =>
        ({
          dispatch,
          state,
        }: {
          dispatch: ((tr: Transaction) => void) | undefined;
          state: EditorState;
        }) => {
          if (!dispatch) return false;
          const typedStorage = this.storage as LineGutterStorage;
          typedStorage.collapsedBlocks.clear();
          const tr = state.tr;
          tr.setMeta(LINE_GUTTER_REBUILD, true);
          dispatch(tr);
          return true;
        },

      collapseAll:
        () =>
        ({
          dispatch,
          state,
        }: {
          dispatch: ((tr: Transaction) => void) | undefined;
          state: EditorState;
        }) => {
          if (!dispatch) return false;
          const typedStorage = this.storage as LineGutterStorage;

          state.doc.descendants((node: ProseMirrorNode) => {
            if (this.options.foldableTypes.includes(node.type.name) && node.attrs.blockId) {
              typedStorage.collapsedBlocks.add(node.attrs.blockId as string);
            }
            return true;
          });

          const tr = state.tr;
          tr.setMeta(LINE_GUTTER_REBUILD, true);
          dispatch(tr);
          return true;
        },

      selectBlock:
        (blockId: string) =>
        ({
          dispatch,
          state,
        }: {
          dispatch: ((tr: Transaction) => void) | undefined;
          state: EditorState;
        }) => {
          if (!dispatch) return false;

          let targetPos: number | null = null;

          state.doc.descendants((node: ProseMirrorNode, pos: number) => {
            if (targetPos !== null) return false;
            const bid = node.attrs.blockId as string | undefined;
            if (bid === blockId) {
              targetPos = pos;
              return false;
            }
            return true;
          });

          if (targetPos === null) return false;

          const tr = state.tr.setSelection(TextSelection.create(state.doc, targetPos + 1));
          tr.setMeta(SELECT_BLOCK_META, blockId);
          dispatch(tr);
          return true;
        },
    };
  },

  addProseMirrorPlugins() {
    const { storage, options, editor } = this;
    const typedStorage = storage as LineGutterStorage;

    return [
      new Plugin({
        key: LINE_GUTTER_KEY,

        state: {
          init(_, state): LineGutterPluginState {
            return {
              selectedBlockId: null,
              decorations: buildGutterDecorations(state, null, typedStorage, options, editor),
            };
          },

          apply(tr, prev, _oldState, newState): LineGutterPluginState {
            // 1. Resolve selectedBlockId changes
            let selectedBlockId = prev.selectedBlockId;
            const selectMeta = tr.getMeta(SELECT_BLOCK_META) as string | null | undefined;
            if (selectMeta !== undefined) {
              selectedBlockId = selectMeta;
            } else if (prev.selectedBlockId !== null && tr.selectionSet) {
              selectedBlockId = null;
            }

            const selectionChanged = selectedBlockId !== prev.selectedBlockId;
            const rebuildMeta = tr.getMeta(LINE_GUTTER_REBUILD) as boolean | undefined;

            // 2. Determine if decorations need rebuilding
            if (tr.docChanged || rebuildMeta || selectionChanged) {
              return {
                selectedBlockId,
                decorations: buildGutterDecorations(
                  newState,
                  selectedBlockId,
                  typedStorage,
                  options,
                  editor
                ),
              };
            }

            // 3. No change — return previous state (zero allocation)
            return prev;
          },
        },

        props: {
          decorations(state) {
            const pluginState = LINE_GUTTER_KEY.getState(state) as
              | LineGutterPluginState
              | undefined;
            return pluginState?.decorations ?? DecorationSet.empty;
          },
        },
      }),
    ];
  },
});

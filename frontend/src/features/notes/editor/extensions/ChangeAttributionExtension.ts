/**
 * ChangeAttributionExtension — TipTap extension for block-level change attribution.
 *
 * T-122: Track which user last edited which block.
 *        Stores `lastEditor` attribute on block nodes (userId, name, timestamp).
 *        On each user transaction that modifies a block, stamps the current
 *        user onto the affected blocks via the `data-last-editor` HTML attr.
 *
 * Spec: specs/016-note-collaboration/spec.md §M6c
 *
 * Design:
 *   - Listens to all ProseMirror transactions via `appendTransaction`.
 *   - Skips no-op, remote CRDT (y-sync), and history transactions.
 *   - Walks changed ranges, finds enclosing block nodes with blockId, stamps them.
 *   - Exposes `editor.storage.changeAttribution.blockAttribution` for UI layer.
 *   - Renders attribution as `data-last-editor-id` + `data-last-editor-name` DOM attrs.
 *
 * @module features/notes/editor/extensions/ChangeAttributionExtension
 */
import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import type { Transaction, EditorState } from '@tiptap/pm/state';

/** Attribution record stored per block. */
export interface BlockAttribution {
  userId: string;
  userName: string;
  /** ISO 8601 timestamp of the last edit. */
  editedAt: string;
}

export interface ChangeAttributionOptions {
  /** Current authenticated user id. */
  userId: string;
  /** Display name for the current user. null when unknown (AI-M9: guard against 'Unknown'). */
  userName: string | null;
}

export interface ChangeAttributionStorage {
  /** blockId → attribution for all blocks that have been edited in this session. */
  blockAttribution: Map<string, BlockAttribution>;
}

const ATTRIBUTION_PLUGIN_KEY = new PluginKey('changeAttribution');
/** Must match BlockIdExtension's attributeName default. */
const ATTR_BLOCK_ID = 'blockId';
const ATTR_LAST_EDITOR_ID = 'lastEditorId';
const ATTR_LAST_EDITOR_NAME = 'lastEditorName';
const ATTR_LAST_EDITED_AT = 'lastEditedAt';

/** Block node types that receive attribution attributes. */
const ATTRIBUTED_BLOCK_TYPES = [
  'paragraph',
  'heading',
  'bulletList',
  'orderedList',
  'listItem',
  'taskList',
  'taskItem',
  'codeBlock',
  'blockquote',
  'horizontalRule',
  'table',
  'pmBlock',
];

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    changeAttribution: {
      /** Manually stamp attribution on a block identified by blockId. */
      stampAttribution: (blockId: string) => ReturnType;
    };
  }
}

export const ChangeAttributionExtension = Extension.create<
  ChangeAttributionOptions,
  ChangeAttributionStorage
>({
  name: 'changeAttribution',

  addOptions(): ChangeAttributionOptions {
    // AI-M9: default userName is null so that attribution is skipped until
    // a real user name is provided, avoiding spurious 'Unknown' attributions.
    return { userId: '', userName: null };
  },

  addStorage(): ChangeAttributionStorage {
    return { blockAttribution: new Map() };
  },

  addGlobalAttributes() {
    return [
      {
        types: ATTRIBUTED_BLOCK_TYPES,
        attributes: {
          [ATTR_LAST_EDITOR_ID]: {
            default: null,
            parseHTML: (element) => element.getAttribute('data-last-editor-id') ?? null,
            renderHTML: (attributes) => {
              const id = attributes[ATTR_LAST_EDITOR_ID] as string | null;
              if (!id) return {};
              return { 'data-last-editor-id': id };
            },
          },
          [ATTR_LAST_EDITOR_NAME]: {
            default: null,
            parseHTML: (element) => element.getAttribute('data-last-editor-name') ?? null,
            renderHTML: (attributes) => {
              const name = attributes[ATTR_LAST_EDITOR_NAME] as string | null;
              if (!name) return {};
              return { 'data-last-editor-name': name };
            },
          },
          [ATTR_LAST_EDITED_AT]: {
            default: null,
            parseHTML: (element) => element.getAttribute('data-last-edited-at') ?? null,
            renderHTML: (attributes) => {
              const ts = attributes[ATTR_LAST_EDITED_AT] as string | null;
              if (!ts) return {};
              return { 'data-last-edited-at': ts };
            },
          },
        },
      },
    ];
  },

  addCommands() {
    return {
      stampAttribution:
        (blockId: string) =>
        ({ tr, state, dispatch }) => {
          const { userId, userName } = this.options;
          // AI-M9: guard — skip stamp when userId or userName is not set
          if (!userId || !userName) return false;

          const now = new Date().toISOString();
          let found = false;

          state.doc.descendants((node, pos) => {
            if (found) return false;
            if (!node.isBlock || node.attrs[ATTR_BLOCK_ID] !== blockId) return;
            found = true;
            if (dispatch) {
              tr.setNodeMarkup(pos, undefined, {
                ...node.attrs,
                [ATTR_LAST_EDITOR_ID]: userId,
                [ATTR_LAST_EDITOR_NAME]: userName,
                [ATTR_LAST_EDITED_AT]: now,
              });
              tr.setMeta('changeAttributionStamp', true);
              dispatch(tr);
            }
            return false;
          });

          if (found) {
            this.storage.blockAttribution.set(blockId, { userId, userName, editedAt: now });
          }

          return found;
        },
    };
  },

  addProseMirrorPlugins() {
    const getOptions = () => this.options;
    const getStorage = () => this.storage;

    return [
      new Plugin({
        key: ATTRIBUTION_PLUGIN_KEY,

        appendTransaction(
          transactions: readonly Transaction[],
          _oldState: EditorState,
          newState: EditorState
        ) {
          // Only process transactions that change document content
          const docChangingTrs = transactions.filter((tr) => tr.docChanged);
          if (docChangingTrs.length === 0) return null;

          const options = getOptions();
          // AI-M9: guard — skip attribution when userId or userName is not set
          if (!options.userId || !options.userName) return null;

          // Skip remote CRDT syncs (y-prosemirror tags these)
          // Skip history (undo/redo) and explicit attribution stamps
          const hasUserEdit = docChangingTrs.some(
            (tr) =>
              !tr.getMeta('y-sync$') &&
              !tr.getMeta('history$') &&
              !tr.getMeta('changeAttributionStamp') &&
              !tr.getMeta('ownershipMigration') &&
              !tr.getMeta('ownershipSetOwner')
          );
          if (!hasUserEdit) return null;

          const now = new Date().toISOString();
          // AI-M9: userName is guaranteed non-null here (guarded above)
          const { userId, userName } = options as { userId: string; userName: string };
          const storage = getStorage();

          // Collect positions of changed blocks
          const changedBlockPositions = new Set<number>();

          for (const tr of docChangingTrs) {
            if (
              tr.getMeta('y-sync$') ||
              tr.getMeta('history$') ||
              tr.getMeta('changeAttributionStamp')
            )
              continue;

            tr.mapping.maps.forEach((stepMap) => {
              stepMap.forEach((oldStart, oldEnd) => {
                // Map old positions to new state positions
                const newFrom = tr.mapping.map(oldStart);
                const newTo = tr.mapping.map(oldEnd);
                newState.doc.nodesBetween(newFrom, newTo, (node, pos) => {
                  if (node.isBlock && node.attrs[ATTR_BLOCK_ID]) {
                    changedBlockPositions.add(pos);
                  }
                });
              });
            });
          }

          if (changedBlockPositions.size === 0) return null;

          const stampTr = newState.tr;
          let stamped = false;

          for (const pos of changedBlockPositions) {
            const node = newState.doc.nodeAt(pos);
            if (!node || !node.isBlock) continue;
            const blockId = node.attrs[ATTR_BLOCK_ID] as string | undefined;
            if (!blockId) continue;

            stampTr.setNodeMarkup(pos, undefined, {
              ...node.attrs,
              [ATTR_LAST_EDITOR_ID]: userId,
              [ATTR_LAST_EDITOR_NAME]: userName,
              [ATTR_LAST_EDITED_AT]: now,
            });
            storage.blockAttribution.set(blockId, { userId, userName, editedAt: now });
            stamped = true;
          }

          if (!stamped) return null;

          stampTr.setMeta('changeAttributionStamp', true);
          return stampTr;
        },
      }),
    ];
  },
});

export default ChangeAttributionExtension;

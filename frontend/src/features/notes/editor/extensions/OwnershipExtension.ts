/**
 * OwnershipExtension — TipTap extension for block-level human/AI ownership (M6b, Feature 016)
 *
 * T-106: `owner` attribute ("human" | "ai:{skill}" | "shared") on all block nodes
 * T-107: filterTransaction guard — rejects human editing AI blocks
 * T-108: Visual decorations — CSS classes for AI/shared blocks, aria-labels
 * T-109: Legacy migration — blocks without owner get "human" on doc load
 *
 * Ownership is authoritative at the backend (C-5). This extension enforces only
 * the UX boundary — MCP tool handlers do the authoritative check.
 *
 * FR-003: AI blocks non-editable by humans (approve/reject only).
 * FR-004: Shared blocks writable by both.
 * FR-009: Legacy blocks default to "human".
 */
import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import type { Transaction } from '@tiptap/pm/state';
import type { Node as ProseMirrorNode } from '@tiptap/pm/model';

/** Block owner type. AI blocks use "ai:{skill-name}" format. */
export type BlockOwner = 'human' | `ai:${string}` | 'shared';

/** Actor performing edits. */
export type EditActor = 'human' | `ai:${string}`;

export interface OwnershipOptions {
  /** Current actor performing edits. Defaults to 'human'. */
  actor: EditActor;
  /**
   * Callback fired when a human tries to edit an AI block (FR-003).
   * Use this to show the edit guard toast.
   */
  onGuardBlock?: (blockId: string, owner: BlockOwner) => void;
}

export interface OwnershipStorage {
  /** Current blockId -> owner map for all blocks in the document. */
  blockOwnership: Map<string, BlockOwner>;
}

const OWNERSHIP_PLUGIN_KEY = new PluginKey<DecorationSet>('ownership');
const ATTR_OWNER = 'owner';
/** Must match BlockIdExtension's attributeName option (default: 'blockId'). */
const ATTR_BLOCK_ID = 'blockId';

/** All block node types that receive the owner attribute. */
const OWNED_BLOCK_TYPES = [
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

export function getBlockOwner(node: ProseMirrorNode): BlockOwner {
  const val = node.attrs[ATTR_OWNER] as string | undefined | null;
  if (val === 'shared' || val === 'human' || (val != null && val.startsWith('ai:'))) {
    return val as BlockOwner;
  }
  return 'human';
}

export function canEdit(actor: EditActor, owner: BlockOwner): boolean {
  if (owner === 'shared') return true;
  if (owner === 'human') return actor === 'human';
  return actor === owner; // ai:{skill} — only matching skill
}

export function extractSkillName(owner: BlockOwner): string {
  return owner.startsWith('ai:') ? owner.slice(3) : owner;
}

export function buildAriaLabel(owner: BlockOwner): string {
  if (owner === 'human') return 'Human block';
  if (owner === 'shared') return 'Shared block — editable by both human and AI';
  return `AI block from ${extractSkillName(owner)}`;
}

function syncStorage(storage: OwnershipStorage, doc: ProseMirrorNode): void {
  storage.blockOwnership.clear();
  doc.descendants((node) => {
    if (!node.isBlock) return;
    const id = node.attrs[ATTR_BLOCK_ID] as string | undefined;
    if (id) storage.blockOwnership.set(id, getBlockOwner(node));
  });
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    ownership: {
      /** Set the owner attribute on a specific block node identified by blockId. */
      setBlockOwner: (blockId: string, owner: BlockOwner) => ReturnType;
      /** Migrate all blocks missing an owner attribute to "human" (T-109). */
      migrateBlockOwners: () => ReturnType;
    };
  }
}

export const OwnershipExtension = Extension.create<OwnershipOptions, OwnershipStorage>({
  name: 'ownership',

  addOptions(): OwnershipOptions {
    return { actor: 'human', onGuardBlock: undefined };
  },

  addStorage(): OwnershipStorage {
    return { blockOwnership: new Map() };
  },

  addCommands() {
    return {
      setBlockOwner:
        (blockId: string, owner: BlockOwner) =>
        ({ tr, state, dispatch }) => {
          let found = false;
          state.doc.descendants((node, pos) => {
            if (found) return false;
            if (!node.isBlock || node.attrs[ATTR_BLOCK_ID] !== blockId) return;
            found = true;
            if (dispatch) {
              tr.setNodeMarkup(pos, undefined, { ...node.attrs, [ATTR_OWNER]: owner });
              tr.setMeta('ownershipSetOwner', true);
              dispatch(tr);
            }
            return false;
          });
          return found;
        },

      migrateBlockOwners:
        () =>
        ({ tr, state, dispatch }) => {
          let changed = false;
          state.doc.descendants((node, pos) => {
            if (!node.isBlock) return;
            const owner = node.attrs[ATTR_OWNER] as string | undefined | null;
            if (!owner) {
              tr.setNodeMarkup(pos, undefined, { ...node.attrs, [ATTR_OWNER]: 'human' });
              changed = true;
            }
          });
          if (changed) {
            tr.setMeta('ownershipMigration', true);
            if (dispatch) dispatch(tr);
          }
          return changed;
        },
    };
  },

  addGlobalAttributes() {
    return [
      {
        types: OWNED_BLOCK_TYPES,
        attributes: {
          [ATTR_OWNER]: {
            default: 'human',
            parseHTML: (element) => (element.getAttribute('data-owner') as BlockOwner) || 'human',
            renderHTML: (attributes) => {
              const owner = (attributes[ATTR_OWNER] as BlockOwner) || 'human';
              return { 'data-owner': owner, 'aria-label': buildAriaLabel(owner) };
            },
          },
        },
      },
    ];
  },

  onCreate() {
    // T-109: Migrate legacy blocks that have no owner attribute
    const { editor } = this;
    if (!editor) return;
    editor.commands.migrateBlockOwners();
    syncStorage(this.storage, editor.state.doc);
  },

  onUpdate() {
    syncStorage(this.storage, this.editor.state.doc);
  },

  addProseMirrorPlugins() {
    const { options } = this;

    return [
      new Plugin({
        key: OWNERSHIP_PLUGIN_KEY,

        // T-107: filterTransaction — reject writes to protected blocks
        filterTransaction(tr: Transaction, state) {
          // Pass migrations, explicit ownership updates, undo/redo history
          if (
            tr.getMeta('ownershipMigration') ||
            tr.getMeta('ownershipSetOwner') ||
            tr.getMeta('history$')
          ) {
            return true;
          }
          // Pass non-content transactions (cursor, focus, selection)
          if (!tr.docChanged) return true;

          const actor = options.actor;

          for (let i = 0; i < tr.steps.length; i++) {
            const step = tr.steps[i];
            if (!step) continue;
            const stepMap = step.getMap();
            let violation = false;
            let violatingBlockId = '';
            let violatingOwner: BlockOwner = 'human';

            stepMap.forEach((oldStart, oldEnd) => {
              if (violation) return;
              state.doc.nodesBetween(oldStart, oldEnd, (node) => {
                if (!node.isBlock || violation) return;
                const owner = getBlockOwner(node);
                if (!canEdit(actor, owner)) {
                  violation = true;
                  violatingBlockId = (node.attrs[ATTR_BLOCK_ID] as string) || '';
                  violatingOwner = owner;
                }
              });
            });

            if (violation) {
              // Use queueMicrotask — cannot call callbacks during filterTransaction
              if (options.onGuardBlock) {
                const bid = violatingBlockId;
                const own = violatingOwner;
                queueMicrotask(() => options.onGuardBlock!(bid, own));
              }
              return false;
            }
          }
          return true;
        },

        props: {
          // T-108: Visual decorations for AI and shared blocks
          decorations(state) {
            const decos: Decoration[] = [];
            state.doc.descendants((node, pos) => {
              if (!node.isBlock) return;
              const owner = getBlockOwner(node);
              if (owner === 'human') return;

              const cls =
                owner === 'shared'
                  ? 'ownership-block ownership-shared'
                  : 'ownership-block ownership-ai';
              const skill = owner === 'shared' ? '' : extractSkillName(owner);

              decos.push(
                Decoration.node(pos, pos + node.nodeSize, {
                  class: cls,
                  'data-owner': owner,
                  'data-skill': skill,
                  'aria-label': buildAriaLabel(owner),
                  role: 'region',
                })
              );
            });
            return DecorationSet.create(state.doc, decos);
          },
        },
      }),
    ];
  },
});

export default OwnershipExtension;

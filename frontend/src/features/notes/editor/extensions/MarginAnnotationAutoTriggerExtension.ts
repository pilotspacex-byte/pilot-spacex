/**
 * MarginAnnotationAutoTriggerExtension - Auto-triggers margin annotation generation
 *
 * Features:
 * - 2000ms typing pause trigger for AI annotation generation
 * - Minimum 50 characters before triggering
 * - 3 blocks of context (current + neighbors)
 * - Prevents duplicate triggers for same block
 * - Integrates with MarginAnnotationStore via callback
 */
import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import type { JSONContent } from '@tiptap/core';

/**
 * Context passed to store when triggering annotation generation
 */
export interface MarginAnnotationContext {
  /** ID of the note being edited */
  noteId: string;
  /** IDs of blocks to annotate (current + context) */
  blockIds: string[];
  /** Current cursor position in document */
  cursorPosition: number;
  /** Type of current block (paragraph, heading, etc.) */
  blockType: string;
  /** Full document content as JSON */
  document: JSONContent;
}

export interface MarginAnnotationAutoTriggerOptions {
  /** Debounce time in ms before triggering AI (default: 2000) */
  debounceMs: number;
  /** Minimum characters in block before triggering (default: 50) */
  minChars: number;
  /** Number of context blocks to include (default: 3) */
  contextBlocks: number;
  /** Whether auto-trigger is enabled */
  enabled: boolean;
  /** Callback when AI should be triggered with context */
  onTrigger?: (context: MarginAnnotationContext) => void;
}

const MARGIN_ANNOTATION_AUTO_TRIGGER_PLUGIN_KEY = new PluginKey('marginAnnotationAutoTrigger');

/**
 * MarginAnnotationAutoTriggerExtension provides automatic AI annotation generation
 *
 * @example
 * ```tsx
 * import { MarginAnnotationAutoTriggerExtension } from './extensions/MarginAnnotationAutoTriggerExtension';
 *
 * const editor = new Editor({
 *   extensions: [
 *     MarginAnnotationAutoTriggerExtension.configure({
 *       debounceMs: 2000,
 *       minChars: 50,
 *       contextBlocks: 3,
 *       onTrigger: (context) => {
 *         // Trigger store to generate annotations via SSE
 *         marginAnnotationStore.autoTriggerAnnotations(
 *           context.noteId,
 *           context.blockIds
 *         );
 *       },
 *     }),
 *   ],
 * });
 * ```
 */
export const MarginAnnotationAutoTriggerExtension =
  Extension.create<MarginAnnotationAutoTriggerOptions>({
    name: 'marginAnnotationAutoTrigger',

    addOptions() {
      return {
        debounceMs: 2000,
        minChars: 50,
        contextBlocks: 3,
        enabled: true,
        onTrigger: undefined,
      };
    },

    addStorage() {
      return {
        debounceTimer: null as ReturnType<typeof setTimeout> | null,
        lastTriggeredBlock: null as string | null,
      };
    },

    addProseMirrorPlugins() {
      // eslint-disable-next-line @typescript-eslint/no-this-alias
      const extension = this;

      return [
        new Plugin({
          key: MARGIN_ANNOTATION_AUTO_TRIGGER_PLUGIN_KEY,

          props: {
            // Handle text input for debounced trigger
            handleTextInput(view) {
              if (!extension.options.enabled || !extension.options.onTrigger) {
                return false;
              }

              // Clear existing debounce timer
              if (extension.storage.debounceTimer) {
                clearTimeout(extension.storage.debounceTimer);
              }

              // Set up debounced AI trigger
              extension.storage.debounceTimer = setTimeout(() => {
                const { state } = view;
                const { selection, doc } = state;
                const $pos = selection.$from;

                // Get current block info
                const resolvedPos = doc.resolve($pos.pos);
                const depth = resolvedPos.depth > 0 ? resolvedPos.depth : 0;
                const blockNode = depth > 0 ? resolvedPos.node(depth) : doc;
                const blockId =
                  (blockNode.attrs?.blockId as string) || `block-${resolvedPos.start(depth)}`;

                // Skip if we already triggered for this block
                if (extension.storage.lastTriggeredBlock === blockId) {
                  return;
                }

                // Calculate block content boundaries
                const blockStart = resolvedPos.start(depth);
                const blockEnd = resolvedPos.end(depth);
                const blockContent = doc.textBetween(blockStart, blockEnd, '\n', '\n');

                // Only trigger if block has enough content
                if (blockContent.length < extension.options.minChars) {
                  return;
                }

                // Collect context block IDs (current + neighbors)
                const blockIds: string[] = [blockId];

                // Try to get previous and next blocks for context
                let contextCollected = 1;
                const maxContext = extension.options.contextBlocks;

                // Walk backwards to find previous blocks
                let prevPos = blockStart - 1;
                while (contextCollected < maxContext && prevPos > 0) {
                  try {
                    const $prevPos = doc.resolve(prevPos);
                    const prevDepth = $prevPos.depth > 0 ? $prevPos.depth : 0;
                    const prevBlock = prevDepth > 0 ? $prevPos.node(prevDepth) : doc;
                    const prevBlockId =
                      (prevBlock.attrs?.blockId as string) || `block-${$prevPos.start(prevDepth)}`;

                    if (prevBlockId !== blockId && !blockIds.includes(prevBlockId)) {
                      blockIds.unshift(prevBlockId);
                      contextCollected++;
                    }

                    prevPos = $prevPos.start(prevDepth) - 1;
                  } catch {
                    break;
                  }
                }

                // Walk forwards to find next blocks
                contextCollected = blockIds.length;
                let nextPos = blockEnd + 1;
                while (contextCollected < maxContext && nextPos < doc.content.size) {
                  try {
                    const $nextPos = doc.resolve(nextPos);
                    const nextDepth = $nextPos.depth > 0 ? $nextPos.depth : 0;
                    const nextBlock = nextDepth > 0 ? $nextPos.node(nextDepth) : doc;
                    const nextBlockId =
                      (nextBlock.attrs?.blockId as string) || `block-${$nextPos.start(nextDepth)}`;

                    if (nextBlockId !== blockId && !blockIds.includes(nextBlockId)) {
                      blockIds.push(nextBlockId);
                      contextCollected++;
                    }

                    nextPos = $nextPos.end(nextDepth) + 1;
                  } catch {
                    break;
                  }
                }

                // Build context for AI
                const context: MarginAnnotationContext = {
                  noteId: '', // Should be provided by parent component
                  blockIds,
                  cursorPosition: $pos.pos,
                  blockType: blockNode.type?.name ?? 'doc',
                  document: doc.toJSON() as JSONContent,
                };

                // Mark this block as triggered
                extension.storage.lastTriggeredBlock = blockId;

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

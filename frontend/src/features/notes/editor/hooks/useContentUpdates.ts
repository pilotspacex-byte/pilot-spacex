/**
 * useContentUpdates hook - Applies AI content updates to TipTap editor.
 *
 * Task 7: Connects PilotSpaceStore's pendingContentUpdates to TipTap editor.
 *
 * Features:
 * - Consumes content_update events from PilotSpaceStore
 * - Applies 3 operation types: replace_block, append_blocks, insert_inline_issue
 * - Conflict detection: AI yields to user editing
 * - Supports both markdown and JSONContent formats
 * - Creates issue records via API when MCP tools provide only issue metadata
 * - Debounces issue creation to prevent duplicates
 *
 * @module features/notes/editor/hooks/useContentUpdates
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { reaction } from 'mobx';
import { toast } from 'sonner';
import type { Editor } from '@tiptap/core';
import type { PilotSpaceStore } from '@/stores/ai/PilotSpaceStore';
import type { ContentUpdateData } from '@/stores/ai/types/events';
import type { Issue } from '@/types';
import {
  highlightBlock,
  handleReplaceBlock,
  handleAppendBlocks,
  handleInsertBlocks,
  handleRemoveBlock,
  handleInsertInlineIssue,
} from './contentUpdateHandlers';

// Re-export highlightBlock for consumers that import from this module
export { highlightBlock } from './contentUpdateHandlers';

/**
 * Retry queue entry for failed content updates.
 */
interface RetryQueueEntry {
  update: ContentUpdateData;
  attemptCount: number;
  nextRetryAt: number;
}

/**
 * Consumes pendingContentUpdates from PilotSpaceStore and applies them
 * to the TipTap editor. Implements conflict detection (AI yields to user).
 *
 * When an insert_inline_issue event arrives without issueId, the hook
 * creates the issue via issuesApi.create() before inserting the node.
 *
 * Features retry mechanism with exponential backoff:
 * - Retry delays: 2s, 4s, 8s (max 3 attempts)
 * - Shows toast notification on conflict
 * - Automatically retries when user moves away from conflicting block
 * - Debounces issue creation to prevent duplicates when AI rapidly extracts issues
 *
 * @param editor - TipTap editor instance
 * @param store - PilotSpaceStore instance
 * @param noteId - Current note ID
 * @param workspaceId - Current workspace ID (needed for issue creation)
 */
export function useContentUpdates(
  editor: Editor | null,
  store: PilotSpaceStore,
  noteId: string,
  workspaceId?: string
): { processingBlockIds: string[]; userEditingBlockId: string | null } {
  // Track in-flight issue creation requests to prevent duplicates (per-instance)
  const inFlightIssuesRef = useRef(new Map<string, Promise<Issue>>());

  // Track user's active editing position for conflict detection
  const userEditingBlockRef = useRef<string | null>(null);
  const [userEditingBlockId, setUserEditingBlockId] = useState<string | null>(null);

  // Retry queue for failed updates (exponential backoff)
  const retryQueueRef = useRef<RetryQueueEntry[]>([]);

  // Track block IDs being processed by AI for visual indicator
  const [processingBlockIds, setProcessingBlockIds] = useState<string[]>([]);

  // Track active timeouts for cleanup on unmount
  const activeTimeoutsRef = useRef(new Set<ReturnType<typeof setTimeout>>());

  // Track user selection changes to detect editing block
  useEffect(() => {
    if (!editor) return;

    const handleSelectionUpdate = () => {
      try {
        const { from } = editor.state.selection;
        const resolvedPos = editor.state.doc.resolve(from);
        const node = resolvedPos.parent;
        const blockId = node?.attrs?.blockId || null;
        userEditingBlockRef.current = blockId;
        setUserEditingBlockId(blockId);
      } catch (error) {
        // Ignore errors during selection tracking
        console.warn('[useContentUpdates] Failed to track selection:', error);
      }
    };

    editor.on('selectionUpdate', handleSelectionUpdate);

    return () => {
      editor.off('selectionUpdate', handleSelectionUpdate);
    };
  }, [editor]);

  // Apply content update to editor
  const applyContentUpdate = useCallback(
    async (
      update: ContentUpdateData,
      userEditingBlockId: string | null,
      isRetry = false
    ): Promise<boolean> => {
      if (!editor) return false;

      // Conflict detection: skip if user is editing the target block
      // Exception: insert_inline_issue is non-destructive (adds inline badge, doesn't replace content)
      const isNonDestructiveOp = update.operation === 'insert_inline_issue';
      if (!isNonDestructiveOp && update.blockId && update.blockId === userEditingBlockId) {
        console.warn(`[AI] Skipping update for block ${update.blockId} - user is editing`);

        // Show toast notification on first conflict (not on retries)
        if (!isRetry) {
          toast.warning('AI update skipped', {
            description: "You're currently editing that block. The AI will retry shortly.",
          });
        }

        return false; // Signal conflict occurred
      }

      try {
        switch (update.operation) {
          case 'replace_block':
            handleReplaceBlock(editor, update);
            break;
          case 'append_blocks':
            handleAppendBlocks(editor, update);
            break;
          case 'insert_blocks':
            handleInsertBlocks(editor, update);
            break;
          case 'remove_block':
            handleRemoveBlock(editor, update);
            break;
          case 'insert_inline_issue':
            await handleInsertInlineIssue(
              editor,
              update,
              workspaceId,
              noteId,
              inFlightIssuesRef.current
            );
            break;
          case 'remove_content':
          case 'replace_content':
            // Inline content operations require server-side processing.
            // Log and skip — these are handled via API re-fetch.
            console.warn(`[AI] ${update.operation} not yet handled in frontend, skipping`);
            return false;
          default:
            console.warn('[AI] Unknown content update operation:', update);
            return false;
        }
        return true; // Success
      } catch (error) {
        console.error('[AI] Failed to apply content update:', error);
        return false;
      }
    },
    [editor, workspaceId, noteId]
  );

  // Add failed update to retry queue with exponential backoff
  const addToRetryQueue = useCallback((update: ContentUpdateData) => {
    const existingEntry = retryQueueRef.current.find(
      (entry) =>
        entry.update.blockId === update.blockId && entry.update.operation === update.operation
    );

    if (existingEntry) {
      // Update existing entry with incremented attempt count
      existingEntry.attemptCount += 1;
      const delayMs = Math.pow(2, existingEntry.attemptCount) * 1000; // 2s, 4s, 8s
      existingEntry.nextRetryAt = Date.now() + delayMs;
    } else {
      // Add new entry
      retryQueueRef.current.push({
        update,
        attemptCount: 1,
        nextRetryAt: Date.now() + 2000, // First retry after 2s
      });
    }
  }, []);

  // Process retry queue periodically
  useEffect(() => {
    if (!editor) return;

    const interval = setInterval(() => {
      const now = Date.now();
      const retryQueue = retryQueueRef.current;

      // Find entries ready for retry
      const readyEntries = retryQueue.filter(
        (entry) => entry.nextRetryAt <= now && entry.attemptCount <= 3
      );

      if (readyEntries.length === 0) return;

      // Process ready entries sequentially to avoid concurrent race conditions
      const processEntries = async () => {
        for (const entry of readyEntries) {
          const success = await applyContentUpdate(
            entry.update,
            userEditingBlockRef.current,
            true // isRetry flag
          );

          if (success) {
            // Remove from queue on success
            const index = retryQueue.indexOf(entry);
            if (index !== -1) {
              retryQueue.splice(index, 1);
            }
          } else if (entry.attemptCount >= 3) {
            // Max retries reached - remove from queue and show error
            const index = retryQueue.indexOf(entry);
            if (index !== -1) {
              retryQueue.splice(index, 1);
            }
            // Clean up processingBlockIds for the failed block
            if (entry.update.blockId) {
              setProcessingBlockIds((prev) => prev.filter((id) => id !== entry.update.blockId));
            }
            console.warn(
              `[AI] Max retries reached for update:`,
              entry.update.operation,
              entry.update.blockId
            );
            toast.error('AI update failed', {
              description: 'Could not apply AI changes after 3 attempts. Please refresh the page.',
            });
          } else {
            // Still conflicting - will retry next interval
            addToRetryQueue(entry.update);
          }
        }
      };
      processEntries().catch((err) => {
        console.error('[AI] Failed to process retry entries:', err);
      });
    }, 1000); // Check every second

    return () => clearInterval(interval);
  }, [editor, applyContentUpdate, addToRetryQueue]);

  // MobX reaction: watch pendingContentUpdates
  useEffect(() => {
    if (!editor || !store) return;

    const dispose = reaction(
      () => store.pendingContentUpdates.length,
      () => {
        // Defer to microtask to avoid flushSync conflict.
        // TipTap's ReactRenderer calls flushSync when creating NodeViews,
        // which conflicts with React's render cycle if triggered from
        // a MobX reaction during observer re-render.
        queueMicrotask(() => {
          // Process all updates for this note
          const processUpdates = async () => {
            let update = store.consumeContentUpdate(noteId);
            while (update) {
              // Add block to processing indicator
              const blockId = update.blockId || update.issueData?.sourceBlockId || null;
              if (blockId) {
                setProcessingBlockIds((prev) =>
                  prev.includes(blockId) ? prev : [...prev, blockId]
                );
              }

              const success = await applyContentUpdate(update, userEditingBlockRef.current);

              // Resolve scroll target: use blockId if available, otherwise detect
              // the last inserted block for append/insert operations (e.g. write_to_note
              // returns blockId=null because content is appended at document end).
              let scrollTargetId = blockId;
              if (success && !scrollTargetId && editor) {
                if (update.operation === 'append_blocks' || update.operation === 'insert_blocks') {
                  const { doc } = editor.state;
                  let lastBlockId: string | null = null;
                  doc.descendants((node) => {
                    const bid = node.attrs?.blockId;
                    if (typeof bid === 'string' && bid) lastBlockId = bid;
                    return true;
                  });
                  scrollTargetId = lastBlockId;
                  if (scrollTargetId) {
                    setProcessingBlockIds((prev) =>
                      prev.includes(scrollTargetId!) ? prev : [...prev, scrollTargetId!]
                    );
                  }
                }
              }

              if (success) {
                // Transition pending-edit → streaming-reveal with CSS bridge
                if (blockId) {
                  store.removePendingAIBlockId(blockId);
                  // Apply streaming-reveal first (CSS bridge handles both classes)
                  // then remove pending-edit after transition completes
                  highlightBlock(blockId, 'streaming-reveal');
                  const transitionTimer = setTimeout(() => {
                    activeTimeoutsRef.current.delete(transitionTimer);
                    const el = document.querySelector(`[data-block-id="${blockId}"]`);
                    if (el) el.classList.remove('ai-block-pending-edit');
                  }, 300); // Match CSS transition duration
                  activeTimeoutsRef.current.add(transitionTimer);
                }

                // Apply visual highlight after successful operation
                if (update.operation === 'replace_block' && blockId) {
                  highlightBlock(blockId, 'streaming-reveal');
                } else if (
                  update.operation === 'append_blocks' ||
                  update.operation === 'insert_blocks'
                ) {
                  // For inserted blocks, highlight the last newly inserted block
                  if (scrollTargetId && scrollTargetId !== blockId) {
                    highlightBlock(scrollTargetId, 'new');
                  } else {
                    // Fallback: try sibling-based detection from anchor
                    const anchorId = update.afterBlockId || update.beforeBlockId;
                    if (anchorId) {
                      const anchorEl = document.querySelector(`[data-block-id="${anchorId}"]`);
                      const sibling = update.beforeBlockId
                        ? anchorEl?.previousElementSibling
                        : anchorEl?.nextElementSibling;
                      const newBlockId = sibling?.getAttribute('data-block-id');
                      if (newBlockId) {
                        highlightBlock(newBlockId, 'new');
                      }
                    }
                  }
                }

                // Delay removal from processingBlockIds so the auto-scroll hook and
                // animation have time to detect and react. Without this delay, React 18
                // batching merges the add+remove into a no-op.
                const targetToClean = scrollTargetId || blockId;
                if (targetToClean) {
                  const processingTimer = setTimeout(() => {
                    activeTimeoutsRef.current.delete(processingTimer);
                    setProcessingBlockIds((prev) => prev.filter((id) => id !== targetToClean));
                  }, 1300); // Match streaming-reveal animation duration
                  activeTimeoutsRef.current.add(processingTimer);
                }
              } else {
                // Failed: remove from processing immediately
                const targetToClean = scrollTargetId || blockId;
                if (targetToClean) {
                  setProcessingBlockIds((prev) => prev.filter((id) => id !== targetToClean));
                }
              }

              // Add to retry queue if conflict occurred
              if (!success && update.blockId) {
                addToRetryQueue(update);
              }

              update = store.consumeContentUpdate(noteId);
            }
          };
          processUpdates().catch((err) => {
            console.error('[AI] Failed to process content updates:', err);
          });
        }); // end queueMicrotask
      }
    );

    // Watch for early AI block IDs from tool_use events — apply pending-edit visual
    // AND add to processingBlockIds so useAIAutoScroll scrolls to the block BEFORE
    // the content_update arrives. This lets the user see the block being prepared.
    const disposePending = reaction(
      () => store.pendingAIBlockIds.length,
      () => {
        for (const blockId of store.pendingAIBlockIds) {
          highlightBlock(blockId, 'pending-edit');
          // Trigger early auto-scroll to the target block
          setProcessingBlockIds((prev) => (prev.includes(blockId) ? prev : [...prev, blockId]));
        }
      }
    );

    // Watch for write_to_note tool_use (no block_id) — scroll to last block in document
    const disposeEndScroll = reaction(
      () => store.pendingNoteEndScroll,
      (shouldScroll) => {
        if (!shouldScroll || !editor) return;
        store.clearNoteEndScroll();
        const { doc } = editor.state;
        let lastBlockId: string | null = null;
        doc.descendants((node) => {
          const bid = node.attrs?.blockId;
          if (typeof bid === 'string' && bid) lastBlockId = bid;
          return true;
        });
        if (lastBlockId) {
          highlightBlock(lastBlockId, 'pending-edit');
          setProcessingBlockIds((prev) =>
            prev.includes(lastBlockId!) ? prev : [...prev, lastBlockId!]
          );
        }
      }
    );

    return () => {
      dispose();
      disposePending();
      disposeEndScroll();
      // Clean up active timeouts to prevent state updates after unmount
      for (const timer of activeTimeoutsRef.current) {
        clearTimeout(timer);
      }
      activeTimeoutsRef.current.clear();
    };
  }, [editor, store, noteId, applyContentUpdate, addToRetryQueue]);

  return { processingBlockIds, userEditingBlockId };
}

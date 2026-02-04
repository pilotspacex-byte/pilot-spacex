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
import { hashString } from '@/lib/debounce';
import type { Issue } from '@/types';

/**
 * Apply a visual highlight to a block after AI completes an operation.
 *
 * - 'edited': background flash from ai-muted to transparent over 1s
 * - 'new': slide-in animation (translateY + opacity) over 300ms
 *
 * Uses direct DOM class manipulation (not ProseMirror decorations) since
 * these are ephemeral visual effects that don't affect editor state.
 */
export function highlightBlock(blockId: string, type: 'edited' | 'new'): void {
  const el = document.querySelector(`[data-block-id="${blockId}"]`);
  if (!el) return;

  if (type === 'edited') {
    el.classList.add('ai-block-edited');
    setTimeout(() => el.classList.add('ai-block-fade-out'), 50);
    setTimeout(() => {
      el.classList.remove('ai-block-edited', 'ai-block-fade-out');
    }, 1100);
  } else {
    el.classList.add('ai-block-new');
    setTimeout(() => el.classList.remove('ai-block-new'), 400);
  }
}

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
): { processingBlockIds: string[] } {
  // Track in-flight issue creation requests to prevent duplicates (per-instance)
  const inFlightIssuesRef = useRef(new Map<string, Promise<Issue>>());

  // Track user's active editing position for conflict detection
  const userEditingBlockRef = useRef<string | null>(null);

  // Retry queue for failed updates (exponential backoff)
  const retryQueueRef = useRef<RetryQueueEntry[]>([]);

  // Track block IDs being processed by AI for visual indicator
  const [processingBlockIds, setProcessingBlockIds] = useState<string[]>([]);

  // Track user selection changes to detect editing block
  useEffect(() => {
    if (!editor) return;

    const handleSelectionUpdate = () => {
      try {
        const { from } = editor.state.selection;
        const resolvedPos = editor.state.doc.resolve(from);
        const node = resolvedPos.parent;
        userEditingBlockRef.current = node?.attrs?.id || null;
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
      if (update.blockId && update.blockId === userEditingBlockId) {
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
          case 'insert_inline_issue':
            await handleInsertInlineIssue(
              editor,
              update,
              workspaceId,
              noteId,
              inFlightIssuesRef.current
            );
            break;
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
        // Process all updates for this note
        const processUpdates = async () => {
          let update = store.consumeContentUpdate(noteId);
          while (update) {
            // Add block to processing indicator
            const blockId = update.blockId || update.issueData?.sourceBlockId || null;
            if (blockId) {
              setProcessingBlockIds((prev) => (prev.includes(blockId) ? prev : [...prev, blockId]));
            }

            const success = await applyContentUpdate(update, userEditingBlockRef.current);

            // Remove block from processing indicator
            if (blockId) {
              setProcessingBlockIds((prev) => prev.filter((id) => id !== blockId));
            }

            // Apply visual highlight after successful operation
            if (success) {
              if (update.operation === 'replace_block' && blockId) {
                highlightBlock(blockId, 'edited');
              } else if (update.operation === 'append_blocks') {
                // For appended blocks, highlight newly inserted blocks after the anchor
                const anchorId = update.afterBlockId;
                if (anchorId) {
                  const anchorEl = document.querySelector(`[data-block-id="${anchorId}"]`);
                  const nextSibling = anchorEl?.nextElementSibling;
                  const newBlockId = nextSibling?.getAttribute('data-block-id');
                  if (newBlockId) {
                    highlightBlock(newBlockId, 'new');
                  }
                }
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
      }
    );

    return () => dispose();
  }, [editor, store, noteId, applyContentUpdate, addToRetryQueue]);

  return { processingBlockIds };
}

/**
 * Handle replace_block operation.
 * Finds node by blockId and replaces its content.
 *
 * Critical safety: validates content is non-empty BEFORE deleting the block.
 * Without this guard, empty/invalid AI responses would delete blocks with no
 * replacement, progressively clearing the document.
 */
function handleReplaceBlock(editor: Editor, update: ContentUpdateData): void {
  if (!update.blockId) {
    console.warn('[AI] replace_block operation missing blockId');
    return;
  }

  // Validate replacement content BEFORE deleting — prevents content clearing
  // when AI sends empty markdown or missing content
  const hasMarkdown =
    update.markdown && typeof update.markdown === 'string' && update.markdown.trim().length > 0;
  const hasContent = update.content && typeof update.content === 'object';

  if (!hasMarkdown && !hasContent) {
    console.warn(
      '[AI] replace_block: no valid content to insert, skipping to prevent content loss',
      {
        blockId: update.blockId,
        markdown: update.markdown,
        contentType: typeof update.content,
      }
    );
    return;
  }

  const { doc } = editor.state;
  let targetPos: number | null = null;
  let targetSize = 0;

  // Find the target block by ID
  doc.descendants((node, pos) => {
    if (node.attrs?.id === update.blockId) {
      targetPos = pos;
      targetSize = node.nodeSize;
      return false; // Stop traversal
    }
    return true; // Continue traversal
  });

  if (targetPos === null) {
    console.warn(`[AI] Block ${update.blockId} not found for replace_block operation`);
    return;
  }

  try {
    // Use markdown if available (preferred), otherwise JSONContent fallback
    // tiptap-markdown extension overrides insertContentAt to parse markdown→HTML
    const contentSource = hasMarkdown ? update.markdown : update.content;
    editor
      .chain()
      .deleteRange({ from: targetPos, to: targetPos + targetSize })
      .insertContentAt(targetPos, contentSource!)
      .run();
  } catch (error) {
    console.error('[AI] Failed to apply replace_block:', error, {
      blockId: update.blockId,
      targetPos,
      targetSize,
    });
  }
}

/**
 * Handle append_blocks operation.
 * Inserts content after target block or at end of document.
 */
function handleAppendBlocks(editor: Editor, update: ContentUpdateData): void {
  const { doc } = editor.state;
  let insertPos = doc.content.size; // Default: end of document

  // Find position after the specified block
  if (update.afterBlockId) {
    doc.descendants((node, pos) => {
      if (node.attrs?.id === update.afterBlockId) {
        insertPos = pos + node.nodeSize;
        return false; // Stop traversal
      }
      return true; // Continue traversal
    });
  }

  // Use markdown if available (preferred), otherwise JSONContent fallback
  // tiptap-markdown extension overrides insertContentAt to parse markdown→HTML
  try {
    if (update.markdown) {
      editor.commands.insertContentAt(insertPos, update.markdown);
    } else if (update.content) {
      editor.commands.insertContentAt(insertPos, update.content);
    } else {
      console.warn('[AI] append_blocks operation missing both markdown and content');
    }
  } catch (error) {
    console.error('[AI] Failed to apply append_blocks:', error, {
      afterBlockId: update.afterBlockId,
      insertPos,
    });
  }
}

/**
 * Handle insert_inline_issue operation.
 * If issueData lacks issueId, creates the issue via API first.
 * Then inserts inline issue node using InlineIssueExtension command.
 *
 * Implements deduplication via title hash to prevent duplicate issues
 * when AI rapidly extracts multiple issues in <500ms.
 */
async function handleInsertInlineIssue(
  editor: Editor,
  update: ContentUpdateData,
  workspaceId?: string,
  _noteId?: string,
  inFlightIssues?: Map<string, Promise<Issue>>
): Promise<void> {
  if (!update.issueData) {
    console.warn('[AI] insert_inline_issue operation missing issueData');
    return;
  }

  let { issueData } = update;

  // If no issueId, create the issue record via API first
  if (!issueData.issueId) {
    if (!workspaceId) {
      console.error('[AI] Cannot create issue: workspaceId not available');
      return;
    }

    // Generate hash for deduplication
    const titleHash = hashString(issueData.title);
    const tracker = inFlightIssues ?? new Map<string, Promise<Issue>>();

    try {
      // Check if issue creation is already in-flight for this title
      let createdIssue: Issue;

      if (tracker.has(titleHash)) {
        // Reuse the existing in-flight request
        console.log(`[AI] Reusing in-flight issue creation for: "${issueData.title}"`);
        createdIssue = await tracker.get(titleHash)!;
      } else {
        // Create new issue and track the promise
        const { issuesApi } = await import('@/services/api/issues');
        const issuePromise = issuesApi.create(workspaceId, {
          name: issueData.title,
          description: issueData.description || '',
          priority: issueData.priority || 'medium',
          type: issueData.type || 'task',
        });

        tracker.set(titleHash, issuePromise);

        try {
          createdIssue = await issuePromise;
        } finally {
          // Clean up tracking after 500ms (debounce window)
          setTimeout(() => {
            tracker.delete(titleHash);
          }, 500);
        }
      }

      // Merge created issue data back
      issueData = {
        ...issueData,
        issueId: createdIssue.id,
        issueKey: createdIssue.identifier,
        title: createdIssue.name,
        type: (createdIssue.type as typeof issueData.type) || 'task',
        state: (createdIssue.state?.group as typeof issueData.state) || 'backlog',
        priority: (createdIssue.priority as typeof issueData.priority) || 'medium',
      };
    } catch (err) {
      console.error('[AI] Failed to create issue from AI extraction:', err);
      return;
    }
  }

  // Use the InlineIssueExtension command
  editor.commands.insertInlineIssue({
    issueId: issueData.issueId!,
    issueKey: issueData.issueKey || '',
    title: issueData.title,
    type: issueData.type || 'task',
    state: issueData.state || 'backlog',
    priority: issueData.priority || 'medium',
    sourceBlockId: issueData.sourceBlockId,
    isNew: true, // Enable animation for newly inserted issues
  });
}

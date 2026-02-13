/**
 * Content update handler functions for AI → TipTap editor operations.
 *
 * Extracted from useContentUpdates to keep the hook file under 700 lines.
 * Each handler is a pure function that takes an Editor and ContentUpdateData,
 * performs the DOM/editor operation, and returns void.
 *
 * @module features/notes/editor/hooks/contentUpdateHandlers
 */

import type { Editor } from '@tiptap/core';
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
export function highlightBlock(
  blockId: string,
  type: 'edited' | 'new' | 'streaming-reveal' | 'pending-edit'
): void {
  const el = document.querySelector(`[data-block-id="${blockId}"]`);
  if (!el) return;

  if (type === 'pending-edit') {
    el.classList.add('ai-block-pending-edit');
    // No auto-removal — removed explicitly when content_update arrives
    return;
  }

  if (type === 'streaming-reveal') {
    el.classList.add('ai-block-streaming-reveal');
    setTimeout(() => el.classList.remove('ai-block-streaming-reveal'), 1300);
  } else if (type === 'edited') {
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
 * Handle replace_block operation.
 * Finds node by blockId and replaces its content.
 *
 * Critical safety: validates content is non-empty BEFORE deleting the block.
 * Without this guard, empty/invalid AI responses would delete blocks with no
 * replacement, progressively clearing the document.
 */
export function handleReplaceBlock(editor: Editor, update: ContentUpdateData): void {
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
    if (node.attrs?.blockId === update.blockId) {
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

    // Preserve original blockId on the first newly inserted node.
    // BlockIdExtension auto-assigns new IDs to inserted nodes, but we need
    // the original ID for highlighting, auto-scroll, and DOM queries.
    const newDoc = editor.state.doc;
    const nodeAtPos = newDoc.nodeAt(targetPos);
    if (nodeAtPos && nodeAtPos.attrs?.blockId !== update.blockId) {
      const { tr } = editor.state;
      tr.setNodeMarkup(targetPos, undefined, {
        ...nodeAtPos.attrs,
        blockId: update.blockId,
      });
      editor.view.dispatch(tr);
    }
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
export function handleAppendBlocks(editor: Editor, update: ContentUpdateData): void {
  const { doc } = editor.state;
  let insertPos = doc.content.size; // Default: end of document

  // Find position after the specified block
  if (update.afterBlockId) {
    doc.descendants((node, pos) => {
      if (node.attrs?.blockId === update.afterBlockId) {
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
 * Handle insert_blocks operation.
 * Inserts content before or after a specified block, or at end of document.
 */
export function handleInsertBlocks(editor: Editor, update: ContentUpdateData): void {
  const { doc } = editor.state;
  let insertPos = doc.content.size; // Default: end of document

  if (update.beforeBlockId) {
    doc.descendants((node, pos) => {
      if (node.attrs?.blockId === update.beforeBlockId) {
        insertPos = pos;
        return false;
      }
      return true;
    });
  } else if (update.afterBlockId) {
    doc.descendants((node, pos) => {
      if (node.attrs?.blockId === update.afterBlockId) {
        insertPos = pos + node.nodeSize;
        return false;
      }
      return true;
    });
  }

  try {
    if (update.markdown) {
      editor.commands.insertContentAt(insertPos, update.markdown);
    } else if (update.content) {
      editor.commands.insertContentAt(insertPos, update.content);
    } else {
      console.warn('[AI] insert_blocks operation missing both markdown and content');
    }
  } catch (error) {
    console.error('[AI] Failed to apply insert_blocks:', error, {
      afterBlockId: update.afterBlockId,
      beforeBlockId: update.beforeBlockId,
      insertPos,
    });
  }
}

/**
 * Handle remove_block operation.
 * Finds node by blockId and deletes it from the document.
 */
export function handleRemoveBlock(editor: Editor, update: ContentUpdateData): void {
  if (!update.blockId) {
    console.warn('[AI] remove_block operation missing blockId');
    return;
  }

  const { doc } = editor.state;
  let targetPos: number | null = null;
  let targetSize = 0;

  doc.descendants((node, pos) => {
    if (node.attrs?.blockId === update.blockId) {
      targetPos = pos;
      targetSize = node.nodeSize;
      return false;
    }
    return true;
  });

  if (targetPos === null) {
    console.warn(`[AI] Block ${update.blockId} not found for remove_block operation`);
    return;
  }

  try {
    editor.commands.deleteRange({ from: targetPos, to: targetPos + targetSize });
  } catch (error) {
    console.error('[AI] Failed to apply remove_block:', error, {
      blockId: update.blockId,
      targetPos,
      targetSize,
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
export async function handleInsertInlineIssue(
  editor: Editor,
  update: ContentUpdateData,
  workspaceId?: string,
  noteId?: string,
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

      // Create NoteIssueLink(EXTRACTED) for bidirectional navigation.
      // Gracefully fails if backend endpoint is not yet available.
      if (noteId) {
        try {
          const { notesApi } = await import('@/services/api/notes');
          await notesApi.linkIssue(
            workspaceId,
            noteId,
            createdIssue.id,
            'EXTRACTED',
            update.blockId ?? undefined
          );
        } catch (linkErr) {
          console.warn('[AI] Failed to create NoteIssueLink(EXTRACTED):', linkErr);
        }
      }
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

/**
 * Handle replace_content operation.
 * Finds text matching oldPattern in target blocks (or all blocks) and replaces
 * with newContent. Supports scoping via blockIds.
 */
export function handleReplaceContent(editor: Editor, update: ContentUpdateData): void {
  const { oldPattern, newContent, blockIds } = update;

  if (!oldPattern) {
    console.warn('[AI] replace_content operation missing oldPattern');
    return;
  }
  if (newContent == null) {
    console.warn('[AI] replace_content operation missing newContent');
    return;
  }

  const { doc, tr } = editor.state;
  let replaced = false;

  doc.descendants((node, pos) => {
    // Skip non-text-bearing nodes
    if (!node.isTextblock) return true;

    // If blockIds specified, only process those blocks
    const nodeBlockId = node.attrs?.blockId;
    if (blockIds && blockIds.length > 0 && !blockIds.includes(nodeBlockId)) {
      return true;
    }

    // Search within this block's text content
    node.descendants((child, childOffset) => {
      if (!child.isText || !child.text) return false;

      const idx = child.text.indexOf(oldPattern);
      if (idx === -1) return false;

      // Calculate absolute position: block pos + 1 (open tag) + child offset + match index
      const from = pos + 1 + childOffset + idx;
      const to = from + oldPattern.length;

      tr.replaceWith(from, to, editor.state.schema.text(newContent));
      replaced = true;

      return false;
    });

    return true;
  });

  if (replaced) {
    editor.view.dispatch(tr);
  } else {
    console.warn('[AI] replace_content: pattern not found in target blocks', {
      oldPattern,
      blockIds,
    });
  }
}

/**
 * Handle remove_content operation.
 * Finds text matching pattern in target blocks (or all blocks) and removes it.
 */
export function handleRemoveContent(editor: Editor, update: ContentUpdateData): void {
  const { pattern } = update;

  if (!pattern) {
    console.warn('[AI] remove_content operation missing pattern');
    return;
  }

  // Reuse replace_content logic with empty replacement
  handleReplaceContent(editor, {
    ...update,
    operation: 'replace_content',
    oldPattern: pattern,
    newContent: '',
  });
}

/**
 * Find the insert position after a specified block, or at end of document.
 * Shared helper for append/insert/pm-block operations.
 */
function findInsertPosition(editor: Editor, afterBlockId: string | null): number {
  const { doc } = editor.state;
  let insertPos = doc.content.size;

  if (afterBlockId) {
    doc.descendants((node, pos) => {
      if (node.attrs?.blockId === afterBlockId) {
        insertPos = pos + node.nodeSize;
        return false;
      }
      return true;
    });
  }

  return insertPos;
}

/**
 * Handle insert_pm_block operation.
 * Inserts a new pmBlock atom node at the specified position.
 * Non-destructive — no conflict detection needed.
 */
export function handleInsertPMBlock(editor: Editor, update: ContentUpdateData): void {
  if (!update.pmBlockData) {
    console.warn('[AI] insert_pm_block operation missing pmBlockData');
    return;
  }

  const { blockType, data, version } = update.pmBlockData;
  const insertPos = findInsertPosition(editor, update.afterBlockId);

  try {
    editor.commands.insertContentAt(insertPos, {
      type: 'pmBlock',
      attrs: {
        blockType,
        data,
        version: version ?? 1,
      },
    });
  } catch (error) {
    console.error('[AI] Failed to insert PM block:', error, {
      blockType,
      afterBlockId: update.afterBlockId,
      insertPos,
    });
  }
}

/**
 * Handle update_pm_block operation.
 * Updates the data attribute of an existing pmBlock node.
 * Checks edit guard — skips if user has manually edited the block.
 */
export function handleUpdatePMBlock(
  editor: Editor,
  update: ContentUpdateData,
  isBlockEdited?: (blockId: string) => boolean
): void {
  if (!update.blockId) {
    console.warn('[AI] update_pm_block operation missing blockId');
    return;
  }

  if (!update.pmBlockData) {
    console.warn('[AI] update_pm_block operation missing pmBlockData');
    return;
  }

  // Respect edit guard (FR-048)
  if (isBlockEdited?.(update.blockId)) {
    console.warn(`[AI] Skipping update_pm_block for user-edited block ${update.blockId}`);
    return;
  }

  const { doc } = editor.state;
  let targetPos: number | null = null;

  doc.descendants((node, pos) => {
    if (node.type.name === 'pmBlock' && node.attrs?.blockId === update.blockId) {
      targetPos = pos;
      return false;
    }
    return true;
  });

  if (targetPos === null) {
    console.warn(`[AI] PM Block ${update.blockId} not found for update_pm_block`);
    return;
  }

  try {
    const { tr } = editor.state;
    const node = doc.nodeAt(targetPos);
    if (!node) return;

    tr.setNodeMarkup(targetPos, undefined, {
      ...node.attrs,
      data: update.pmBlockData.data,
      ...(update.pmBlockData.version != null && { version: update.pmBlockData.version }),
    });
    editor.view.dispatch(tr);
  } catch (error) {
    console.error('[AI] Failed to update PM block:', error, {
      blockId: update.blockId,
      targetPos,
    });
  }
}

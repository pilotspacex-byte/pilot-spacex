/**
 * useSelectionContext - Track editor selection and sync to PilotSpaceStore
 * Enables contextual AI interactions based on selected content
 */

import { useEffect, useCallback } from 'react';
import type { Editor } from '@tiptap/core';
import type { PilotSpaceStore } from '@/stores/ai/PilotSpaceStore';

export interface SelectionContext {
  selectedText: string;
  selectedBlockIds: string[];
  cursorPosition: number;
}

/**
 * Hook to track editor selection and update PilotSpace store context.
 * Debounces updates to avoid excessive store mutations.
 *
 * @param editor - TipTap editor instance
 * @param store - PilotSpaceStore instance
 * @param noteId - Current note ID
 * @param debounceMs - Debounce delay in milliseconds (default: 300ms)
 */
export function useSelectionContext(
  editor: Editor | null,
  store: PilotSpaceStore,
  noteId: string,
  debounceMs = 300
): SelectionContext | null {
  const updateContext = useCallback(() => {
    if (!editor || !noteId) return null;

    const { from, to, empty } = editor.state.selection;

    // Extract selected text
    const selectedText = empty ? '' : editor.state.doc.textBetween(from, to);

    // Extract block IDs from selected range
    const selectedBlockIds: string[] = [];
    editor.state.doc.nodesBetween(from, to, (node) => {
      const blockId = node.attrs?.id || node.attrs?.blockId;
      if (blockId && !selectedBlockIds.includes(blockId)) {
        selectedBlockIds.push(blockId);
      }
      return true;
    });

    const context: SelectionContext = {
      selectedText,
      selectedBlockIds,
      cursorPosition: from,
    };

    // Update store context
    store.setNoteContext({
      noteId,
      selectedText: selectedText || undefined,
      selectedBlockIds: selectedBlockIds.length > 0 ? selectedBlockIds : undefined,
    });

    return context;
  }, [editor, store, noteId]);

  // Track selection changes with debouncing
  useEffect(() => {
    if (!editor) return;

    let timeoutId: NodeJS.Timeout;

    const handleSelectionUpdate = () => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        updateContext();
      }, debounceMs);
    };

    // Listen to selection updates
    editor.on('selectionUpdate', handleSelectionUpdate);

    // Initial update
    handleSelectionUpdate();

    return () => {
      editor.off('selectionUpdate', handleSelectionUpdate);
      clearTimeout(timeoutId);
    };
  }, [editor, updateContext, debounceMs]);

  return null; // Hook doesn't return value, updates store directly
}

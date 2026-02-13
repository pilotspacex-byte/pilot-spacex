/**
 * useBlockEditGuard - Hook tracking user edits on PM blocks (FR-048).
 *
 * When a user manually edits a PM block, the block is marked as `userEdited`.
 * The Agent MUST NOT modify blocks marked as user-edited; it generates new
 * blocks for revisions instead.
 *
 * FR-048: The Agent MUST NOT modify PM blocks that the user has manually edited.
 *
 * Usage:
 * - Call `markEdited(blockId)` when the user modifies a block's content or attrs.
 * - Call `isEdited(blockId)` to check if a block has been user-edited.
 * - The Agent integration layer checks `isEdited` before applying content updates.
 * - `clearEdited(blockId)` is available for undo/reset scenarios.
 *
 * State is stored in `editor.storage.blockEditGuard` so it survives re-renders
 * and is accessible from TipTap extension code.
 */
import { useCallback, useEffect, useRef } from 'react';
import type { Editor } from '@tiptap/core';

/** Storage key used in editor.storage */
const STORAGE_KEY = 'blockEditGuard';

interface BlockEditGuardStorage {
  editedBlockIds: Set<string>;
}

function getStorage(editor: Editor): BlockEditGuardStorage {
  const storage = editor.storage as unknown as Record<string, unknown>;
  if (!storage[STORAGE_KEY]) {
    storage[STORAGE_KEY] = { editedBlockIds: new Set<string>() };
  }
  return storage[STORAGE_KEY] as BlockEditGuardStorage;
}

export interface BlockEditGuard {
  /** Mark a block as user-edited. Agent will not overwrite it. */
  markEdited: (blockId: string) => void;
  /** Check if a block has been user-edited. */
  isEdited: (blockId: string) => boolean;
  /** Clear user-edited flag (for undo/reset). */
  clearEdited: (blockId: string) => void;
  /** Get all user-edited block IDs. */
  getEditedBlockIds: () => string[];
}

/**
 * Hook that provides an edit guard for PM blocks within a TipTap editor.
 * Returns stable callbacks that read/write from `editor.storage`.
 *
 * @param editor - The TipTap editor instance (can be null during initialization).
 * @returns BlockEditGuard with markEdited, isEdited, clearEdited, getEditedBlockIds.
 *
 * @example
 * ```tsx
 * const { markEdited, isEdited } = useBlockEditGuard(editor);
 *
 * // In a PM block component's onChange handler:
 * function handleFieldChange(blockId: string, field: string, value: string) {
 *   updateBlockData(blockId, field, value);
 *   markEdited(blockId);
 * }
 *
 * // In agent content update handler:
 * if (isEdited(blockId)) {
 *   // Skip — user has edited this block
 *   return;
 * }
 * ```
 */
export function useBlockEditGuard(editor: Editor | null): BlockEditGuard {
  const editorRef = useRef(editor);

  // Sync ref in effect to avoid ref update during render
  useEffect(() => {
    editorRef.current = editor;
  }, [editor]);

  // Initialize storage on editor creation
  useEffect(() => {
    if (editor && !editor.isDestroyed) {
      getStorage(editor);
    }
  }, [editor]);

  const markEdited = useCallback((blockId: string) => {
    const ed = editorRef.current;
    if (!ed || ed.isDestroyed) return;
    getStorage(ed).editedBlockIds.add(blockId);
  }, []);

  const isEdited = useCallback((blockId: string): boolean => {
    const ed = editorRef.current;
    if (!ed || ed.isDestroyed) return false;
    return getStorage(ed).editedBlockIds.has(blockId);
  }, []);

  const clearEdited = useCallback((blockId: string) => {
    const ed = editorRef.current;
    if (!ed || ed.isDestroyed) return;
    getStorage(ed).editedBlockIds.delete(blockId);
  }, []);

  const getEditedBlockIds = useCallback((): string[] => {
    const ed = editorRef.current;
    if (!ed || ed.isDestroyed) return [];
    return Array.from(getStorage(ed).editedBlockIds);
  }, []);

  return { markEdited, isEdited, clearEdited, getEditedBlockIds };
}

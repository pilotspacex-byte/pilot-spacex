/**
 * useSelectionAIActions - AI action handlers for text selection
 * Provides handlers for Ask Pilot, Enhance, and Extract Issues actions
 */

import { useCallback } from 'react';
import type { Editor } from '@tiptap/core';
import type { PilotSpaceStore } from '@/stores/ai/PilotSpaceStore';

export interface SelectionAIActionsResult {
  /** Open ChatView with selected text as context */
  askPilot: () => Promise<void>;
  /** Enhance selected text with AI */
  enhanceSelection: () => Promise<void>;
  /** Extract issues from selected content */
  extractIssues: () => Promise<void>;
  /** Check if selection has content */
  hasSelection: boolean;
  /** Get current selected text */
  getSelectedText: () => string;
}

/**
 * Hook to provide AI action handlers for text selection.
 * Integrates with SelectionToolbar to trigger AI operations.
 *
 * @param editor - TipTap editor instance
 * @param store - PilotSpaceStore for AI operations
 * @param noteId - Current note ID
 * @param onChatViewOpen - Callback to open ChatView (optional)
 * @returns Action handlers and selection state
 *
 * @example
 * ```tsx
 * const { askPilot, enhanceSelection, extractIssues } = useSelectionAIActions(
 *   editor,
 *   aiStore.pilotSpace,
 *   noteId,
 *   () => setIsChatViewOpen(true)
 * );
 *
 * // In SelectionToolbar
 * <Button onClick={askPilot}>Ask Pilot</Button>
 * ```
 */
export function useSelectionAIActions(
  editor: Editor | null,
  store: PilotSpaceStore,
  noteId: string,
  onChatViewOpen?: () => void
): SelectionAIActionsResult {
  /**
   * Get selected text from editor.
   */
  const getSelectedText = useCallback((): string => {
    if (!editor) return '';
    const { from, to, empty } = editor.state.selection;
    if (empty) return '';
    return editor.state.doc.textBetween(from, to);
  }, [editor]);

  /**
   * Check if editor has active selection.
   */
  const hasSelection = !!editor && !editor.state.selection.empty;

  /**
   * Ask Pilot action - Opens ChatView with selection as context.
   * Pre-fills the conversation context with selected text and blocks.
   */
  const askPilot = useCallback(async (): Promise<void> => {
    if (!editor || !noteId) return;

    const { from, to, empty } = editor.state.selection;
    if (empty) return;

    const selectedText = editor.state.doc.textBetween(from, to);

    // Extract block IDs from selection
    const selectedBlockIds: string[] = [];
    editor.state.doc.nodesBetween(from, to, (node) => {
      const blockId = node.attrs?.id || node.attrs?.blockId;
      if (blockId && !selectedBlockIds.includes(blockId)) {
        selectedBlockIds.push(blockId);
      }
      return true;
    });

    // Update store context (will be picked up by ChatInput's ContextIndicator)
    store.setNoteContext({
      noteId,
      selectedText,
      selectedBlockIds: selectedBlockIds.length > 0 ? selectedBlockIds : undefined,
    });

    // Open ChatView if callback provided
    if (onChatViewOpen) {
      onChatViewOpen();
    }
  }, [editor, store, noteId, onChatViewOpen]);

  /**
   * Enhance selection action - Sends enhance request directly.
   * AI will stream back improved version.
   */
  const enhanceSelection = useCallback(async (): Promise<void> => {
    if (!editor || !noteId) return;

    const selectedText = getSelectedText();
    if (!selectedText) return;

    // Extract block IDs for context
    const { from, to } = editor.state.selection;
    const selectedBlockIds: string[] = [];
    editor.state.doc.nodesBetween(from, to, (node) => {
      const blockId = node.attrs?.id || node.attrs?.blockId;
      if (blockId && !selectedBlockIds.includes(blockId)) {
        selectedBlockIds.push(blockId);
      }
      return true;
    });

    // Set context before sending message
    store.setNoteContext({
      noteId,
      selectedText,
      selectedBlockIds: selectedBlockIds.length > 0 ? selectedBlockIds : undefined,
    });

    // Send enhance request
    await store.sendMessage(`Enhance the following text: ${selectedText}`);

    // Open ChatView to show response
    if (onChatViewOpen) {
      onChatViewOpen();
    }
  }, [editor, store, noteId, getSelectedText, onChatViewOpen]);

  /**
   * Extract issues action - Sends extract issues request.
   * AI will analyze selection and extract actionable items.
   */
  const extractIssues = useCallback(async (): Promise<void> => {
    if (!editor || !noteId) return;

    const selectedText = getSelectedText();
    if (!selectedText) return;

    // Extract block IDs for source tracking
    const { from, to } = editor.state.selection;
    const selectedBlockIds: string[] = [];
    editor.state.doc.nodesBetween(from, to, (node) => {
      const blockId = node.attrs?.id || node.attrs?.blockId;
      if (blockId && !selectedBlockIds.includes(blockId)) {
        selectedBlockIds.push(blockId);
      }
      return true;
    });

    // Set context with source blocks
    store.setNoteContext({
      noteId,
      selectedText,
      selectedBlockIds: selectedBlockIds.length > 0 ? selectedBlockIds : undefined,
    });

    // Send extract request
    await store.sendMessage(`Extract actionable issues from: ${selectedText}`);

    // Open ChatView to show extracted issues
    if (onChatViewOpen) {
      onChatViewOpen();
    }
  }, [editor, store, noteId, getSelectedText, onChatViewOpen]);

  return {
    askPilot,
    enhanceSelection,
    extractIssues,
    hasSelection,
    getSelectedText,
  };
}

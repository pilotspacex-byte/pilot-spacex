/**
 * useEditorSync - Synchronizes MobX AI stores with TipTap editor.
 *
 * Extracted from NoteCanvas to reduce file size.
 * Handles:
 * - Ghost text suggestion sync (MobX reaction → editor commands)
 * - Margin annotation sync (MobX reaction → editor extension)
 * - Annotation fetch on mount
 *
 * @module components/editor/hooks/useEditorSync
 */
import { useEffect } from 'react';
import { reaction } from 'mobx';
import type { Editor } from '@tiptap/core';
import type { AIStore } from '@/stores/ai/AIStore';

/**
 * Sync ghost text suggestions and margin annotations from MobX stores
 * to the TipTap editor instance via MobX reactions.
 *
 * @param editorRef - Mutable ref to the current TipTap editor
 * @param isEditorReady - Whether the editor has been created
 * @param aiStore - AIStore instance (contains ghostText and marginAnnotation stores)
 * @param noteId - Current note ID
 * @param workspaceSlug - Current workspace slug (for annotation fetch)
 * @param editor - TipTap editor instance (for annotation fetch dependency)
 */
export function useEditorSync(
  editorRef: React.MutableRefObject<Editor | null>,
  isEditorReady: boolean,
  aiStore: AIStore,
  noteId: string,
  workspaceSlug: string,
  editor: Editor | null
): void {
  // Sync ghost text suggestion from store to editor
  useEffect(() => {
    const currentEditor = editorRef.current;
    if (!currentEditor || currentEditor.isDestroyed) return;

    const disposer = reaction(
      () => aiStore.ghostText.suggestion,
      (suggestion: string) => {
        // Defer to avoid flushSync conflict: TipTap's ReactRenderer calls
        // flushSync when dispatching transactions, which conflicts with
        // React's render cycle if triggered from a MobX reaction.
        queueMicrotask(() => {
          if (!currentEditor.isDestroyed) {
            if (suggestion) {
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              (currentEditor.commands as any).setGhostText?.(suggestion);
            } else {
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              (currentEditor.commands as any).dismissGhostText?.();
            }
          }
        });
      },
      { fireImmediately: true }
    );

    return () => disposer();
  }, [isEditorReady, aiStore.ghostText, editorRef]);

  // Sync margin annotations from store to editor extension
  useEffect(() => {
    if (!isEditorReady || !noteId) return;

    const disposer = reaction(
      () => aiStore.marginAnnotation.getAnnotationsForNote(noteId),
      (storeAnnotations) => {
        // Defer to avoid flushSync conflict with TipTap's ReactRenderer.
        queueMicrotask(() => {
          // Build annotation data map for editor extension
          const annotationMap = new Map();
          storeAnnotations.forEach((annotation) => {
            const existing = annotationMap.get(annotation.blockId) || {
              blockId: annotation.blockId,
              count: 0,
              types: [],
            };
            existing.count += 1;
            if (!existing.types.includes(annotation.type)) {
              existing.types.push(annotation.type);
            }
            annotationMap.set(annotation.blockId, existing);
          });

          // Update editor extension
          const currentEditor = editorRef.current;
          if (currentEditor && !currentEditor.isDestroyed) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (currentEditor.commands as any).setAnnotations?.(annotationMap);
          }
        });
      },
      { fireImmediately: true }
    );

    return () => disposer();
  }, [isEditorReady, noteId, aiStore.marginAnnotation, editorRef]);

  // Fetch persisted annotations on mount
  useEffect(() => {
    if (noteId && workspaceSlug && editor && !editor.isDestroyed) {
      aiStore.marginAnnotation.fetchAnnotations(workspaceSlug, noteId);
    }
  }, [noteId, workspaceSlug, editor, aiStore.marginAnnotation]);
}

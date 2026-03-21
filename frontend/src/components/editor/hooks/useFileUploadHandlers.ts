/**
 * useFileUploadHandlers — Drop handler and slash command upload listener for TipTap editor.
 *
 * Provides:
 * - `handleDrop`: ProseMirror handleDOMEvents.drop handler for drag-and-drop file uploads
 * - `setupUploadListener`: registers pilot:upload-artifact event listener on editor DOM
 *
 * Uses refs for workspaceId/projectId to avoid stale closures in useEditor callbacks.
 */
import { useEffect, useRef } from 'react';
import type { EditorView } from '@tiptap/pm/view';
import type { Editor } from '@tiptap/core';
import { uploadFileAndUpdateNode } from '@/features/notes/editor/config';

interface FileUploadRefs {
  resolvedWorkspaceIdRef: React.RefObject<string | undefined>;
  projectIdRef: React.RefObject<string | undefined>;
  editorRef: React.RefObject<Editor | null>;
}

/**
 * Creates a ProseMirror drop handler that inserts figure/fileCard nodes
 * and triggers uploads via uploadFileAndUpdateNode.
 */
export function createDropHandler(refs: FileUploadRefs) {
  return (view: EditorView, event: DragEvent): boolean => {
    const files = event.dataTransfer?.files;
    if (!files?.length) return false;

    event.preventDefault();

    const coords = view.posAtCoords({ left: event.clientX, top: event.clientY });
    const insertPos = coords?.pos ?? view.state.doc.content.size;

    for (const file of Array.from(files)) {
      const isImage = file.type.startsWith('image/');
      const nodeType = isImage ? 'figure' : 'fileCard';

      const nodeAttrs = isImage
        ? { src: null, alt: file.name, artifactId: null, status: 'uploading' }
        : {
            artifactId: null,
            filename: file.name,
            mimeType: file.type,
            sizeBytes: file.size,
            status: 'uploading',
          };

      try {
        const nodeJSON = {
          type: nodeType,
          attrs: nodeAttrs,
          ...(isImage ? { content: [] } : {}),
        };
        view.dispatch(view.state.tr.insert(insertPos, view.state.schema.nodeFromJSON(nodeJSON)));
      } catch {
        continue;
      }

      if (
        refs.resolvedWorkspaceIdRef.current &&
        refs.projectIdRef.current &&
        refs.editorRef.current
      ) {
        void uploadFileAndUpdateNode(
          refs.editorRef.current,
          file,
          nodeType,
          refs.resolvedWorkspaceIdRef.current,
          refs.projectIdRef.current
        );
      }
    }
    return true;
  };
}

/**
 * Registers the pilot:upload-artifact event listener on the editor DOM element.
 * Called from useEditor's onCreate callback.
 */
export function setupUploadListener(ed: Editor, refs: FileUploadRefs): void {
  ed.view.dom.addEventListener('pilot:upload-artifact', (e) => {
    const customEvent = e as CustomEvent<{
      file: File;
      nodeType: 'figure' | 'fileCard';
      editor: Editor;
    }>;
    const { file, nodeType } = customEvent.detail;
    if (refs.resolvedWorkspaceIdRef.current && refs.projectIdRef.current) {
      void uploadFileAndUpdateNode(
        customEvent.detail.editor,
        file,
        nodeType,
        refs.resolvedWorkspaceIdRef.current,
        refs.projectIdRef.current
      );
    }
  });
}

/**
 * Hook that creates and maintains refs for file upload handlers.
 * Returns refs and handler factories for use in useEditor options.
 */
export function useFileUploadRefs(
  resolvedWorkspaceId: string | undefined,
  projectId: string | undefined,
  editorRef: React.RefObject<Editor | null>
) {
  const resolvedWorkspaceIdRef = useRef<string | undefined>(undefined);
  const projectIdRef = useRef<string | undefined>(projectId);

  useEffect(() => {
    resolvedWorkspaceIdRef.current = resolvedWorkspaceId;
    projectIdRef.current = projectId;
  }, [resolvedWorkspaceId, projectId]);

  return { resolvedWorkspaceIdRef, projectIdRef, editorRef };
}

'use client';

/**
 * FilePreviewConfigContext — React context providing workspace and project identifiers
 * needed for signed URL fetching in the inline file preview.
 *
 * Follows the same context bridge pattern as FileCardContext and IssueNoteContext:
 * - Provided by the note/issue page that hosts the TipTap editor
 * - Consumed by useInlinePreviewContent to fetch signed URLs without prop drilling
 *   through TipTap's NodeView boundary
 *
 * Usage:
 *   <FilePreviewConfigContext.Provider value={{ workspaceId, projectId }}>
 *     <NoteCanvas ... />
 *   </FilePreviewConfigContext.Provider>
 */

import { createContext, useContext } from 'react';

export interface FilePreviewConfig {
  workspaceId: string;
  projectId: string;
}

export const FilePreviewConfigContext = createContext<FilePreviewConfig | null>(null);

/**
 * Returns the file preview config from context.
 * Throws if the context has not been provided — callers must be wrapped in
 * FilePreviewConfigContext.Provider at the page level.
 */
export function useFilePreviewConfig(): FilePreviewConfig {
  const ctx = useContext(FilePreviewConfigContext);
  if (!ctx) {
    throw new Error(
      'useFilePreviewConfig must be used within a FilePreviewConfigContext.Provider'
    );
  }
  return ctx;
}

/**
 * Safe variant that returns null when the context provider is absent.
 * Used by useInlinePreviewContent to gracefully fall back to non-previewable
 * behavior when a FileCard is rendered outside a page-level provider.
 */
export function useFilePreviewConfigSafe(): FilePreviewConfig | null {
  return useContext(FilePreviewConfigContext);
}

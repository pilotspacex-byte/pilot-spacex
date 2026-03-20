'use client';

/**
 * FileCardContext — React context bridge for FileCardNodeView → FileCardView.
 *
 * Follows the NodeView context bridge pattern documented in node-view-bridge.ts:
 * - FileCardNodeView (plain, NOT observer) creates the context value from node.attrs
 * - FileCardView (observer) reads from this context to render with MobX reactivity
 *
 * This prevents the flushSync conflict that occurs when observer() is used directly
 * on a ReactNodeViewRenderer-mounted component in React 19.
 */
import { createContext, useContext } from 'react';

export interface FileCardContextValue {
  artifactId: string | null;
  filename: string;
  mimeType: string;
  sizeBytes: number;
  status: 'uploading' | 'ready' | 'error';
  readOnly: boolean;
  updateAttributes: (
    attrs: Partial<{
      artifactId: string | null;
      filename: string;
      mimeType: string;
      sizeBytes: number;
      status: 'uploading' | 'ready' | 'error';
    }>
  ) => void;
}

export const FileCardContext = createContext<FileCardContextValue | null>(null);

export function useFileCardContext(): FileCardContextValue {
  const ctx = useContext(FileCardContext);
  if (!ctx) throw new Error('useFileCardContext must be used within FileCardContext.Provider');
  return ctx;
}

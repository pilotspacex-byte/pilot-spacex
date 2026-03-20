'use client';

/**
 * FileCardNodeView — Plain (non-observer) NodeView wrapper for FileCardExtension.
 *
 * IMPORTANT: Do NOT wrap this component in observer(). ReactNodeViewRenderer creates
 * NodeViews inside ProseMirror transactions during React's render lifecycle.
 * observer() uses useSyncExternalStore which calls flushSync internally,
 * causing "flushSync was called from inside a lifecycle method" in React 19.
 *
 * Pattern: plain wrapper → context bridge → FileCardView (observer child).
 * Source: frontend/src/features/issues/components/issue-editor-content.tsx
 * See: frontend/src/features/notes/editor/extensions/node-view-bridge.ts
 */
import { NodeViewWrapper, type NodeViewProps } from '@tiptap/react';
import { FileCardContext, type FileCardContextValue } from './FileCardContext';
import { FileCardView } from './FileCardView';

export function FileCardNodeView({ node, updateAttributes, editor }: NodeViewProps) {
  const attrs = node.attrs as {
    artifactId: string | null;
    filename: string;
    mimeType: string;
    sizeBytes: number;
    status: 'uploading' | 'ready' | 'error';
  };

  const contextValue: FileCardContextValue = {
    artifactId: attrs.artifactId,
    filename: attrs.filename,
    mimeType: attrs.mimeType,
    sizeBytes: attrs.sizeBytes,
    status: attrs.status,
    readOnly: !editor.isEditable,
    updateAttributes,
  };

  return (
    <NodeViewWrapper>
      <FileCardContext.Provider value={contextValue}>
        <FileCardView />
      </FileCardContext.Provider>
    </NodeViewWrapper>
  );
}

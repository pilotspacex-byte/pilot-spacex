'use client';

/**
 * EditorLayout - Three-panel resizable layout for the IDE editor.
 *
 * Panels:
 * 1. File tree (left) - Collapsible, 20% default (~240px), max 30% (~400px)
 * 2. Editor (center) - Fills remaining space, min 40%
 *
 * Preview is NOT a separate panel -- it replaces editor content via toggle
 * (per UI-SPEC: "appears only in preview mode, replaces editor").
 *
 * Features:
 * - Crossfade transitions for mode/file switches (200ms opacity)
 * - Auto-save via useAutoSaveEditor (2s debounce + Cmd+S flush)
 * - QuickOpen overlay (Cmd+P) always available
 * - MobX observer for reactive FileStore state
 */

import { useCallback, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { observer } from 'mobx-react-lite';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import { Skeleton } from '@/components/ui/skeleton';
import { useFileStore } from '@/stores/RootStore';
import { FileTree } from '@/features/file-browser/components/FileTree';
import { TabBar } from '@/features/file-browser/components/TabBar';
import { QuickOpen } from '@/features/file-browser/components/QuickOpen';
import { useAutoSaveEditor } from './hooks/useAutoSaveEditor';
import type { FileTreeItem } from '@/features/file-browser/hooks/useFileTree';

const MonacoNoteEditor = dynamic(() => import('./MonacoNoteEditor'), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full" />,
});

const MonacoFileEditor = dynamic(() => import('./MonacoFileEditor'), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full" />,
});

interface EditorLayoutProps {
  fileTreeItems: FileTreeItem[];
  className?: string;
  /** Persistence callback: receives file ID and content string. Called by auto-save (2s debounce) and Cmd+S. */
  onSave?: (fileId: string, content: string) => Promise<void>;
}

/** Empty state shown when no file is open. */
function EmptyEditor() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center">
      <h2 className="text-lg font-semibold">Nothing open</h2>
      <p className="text-muted-foreground mt-2">
        Open a file from the sidebar, or press Cmd+P to search.
      </p>
    </div>
  );
}

export const EditorLayout = observer(function EditorLayout({
  fileTreeItems,
  className,
  onSave,
}: EditorLayoutProps) {
  const fileStore = useFileStore();
  const activeFile = fileStore.activeFile;

  // Auto-save: delegates to parent-provided onSave callback (no-op if not provided)
  const saveFn = useCallback(
    async (id: string, content: string) => {
      if (onSave) {
        await onSave(id, content);
      }
    },
    [onSave]
  );

  useAutoSaveEditor(activeFile?.id ?? null, activeFile?.content ?? '', saveFn);

  // Handle editor content changes
  const handleNoteChange = useCallback(
    (content: string) => {
      if (activeFile) {
        fileStore.updateContent(activeFile.id, content);
      }
    },
    [activeFile, fileStore]
  );

  const handleFileChange = useCallback(
    (content: string) => {
      if (activeFile) {
        fileStore.updateContent(activeFile.id, content);
      }
    },
    [activeFile, fileStore]
  );

  // Memoize items for QuickOpen (flatten to files only)
  const quickOpenItems = useMemo(() => fileTreeItems, [fileTreeItems]);

  return (
    <div className={className}>
      <ResizablePanelGroup orientation="horizontal">
        {/* File Tree - left panel */}
        <ResizablePanel defaultSize={20} minSize={0} maxSize={30} collapsible>
          <div className="h-full transition-all duration-200">
            <FileTree items={fileTreeItems} className="h-full" />
          </div>
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* Editor - center panel */}
        <ResizablePanel defaultSize={80} minSize={40}>
          <div className="flex flex-col h-full">
            <TabBar />

            {/* Crossfade transition wrapper */}
            <div className="flex-1 relative overflow-hidden">
              <div className="absolute inset-0 transition-opacity duration-200">
                {activeFile ? (
                  activeFile.source === 'note' ? (
                    <MonacoNoteEditor
                      noteId={activeFile.id}
                      initialContent={activeFile.content}
                      onChange={handleNoteChange}
                      isReadOnly={activeFile.isReadOnly}
                      className="h-full"
                    />
                  ) : (
                    <MonacoFileEditor file={activeFile} onChange={handleFileChange} />
                  )
                ) : (
                  <EmptyEditor />
                )}
              </div>
            </div>
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>

      {/* QuickOpen overlay - always available */}
      <QuickOpen items={quickOpenItems} />
    </div>
  );
});

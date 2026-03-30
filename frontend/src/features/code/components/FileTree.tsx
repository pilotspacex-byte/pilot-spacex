'use client';

import { useCallback } from 'react';
import { observer } from 'mobx-react-lite';
import { Virtuoso } from 'react-virtuoso';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useFileStore } from '@/stores/RootStore';
import { useFileTree, type FileTreeItem } from '../hooks/useFileTree';
import { FileTreeNode } from './FileTreeNode';
import { getLanguageLabel } from '../types';
import { cn } from '@/lib/utils';
import type { Artifact } from '@/types/artifact';

interface FileTreeProps {
  /** Flat artifact list from the project. Tree structure is derived internally. */
  artifacts: Artifact[];
  /** Called when the user clicks a file node. */
  onFileSelect: (artifact: Artifact) => void;
  projectId: string;
  className?: string;
}

export const FileTree = observer(function FileTree({
  artifacts,
  onFileSelect,
  className,
}: FileTreeProps) {
  const fileStore = useFileStore();

  // Transform artifacts into FileTreeItems for the tree hook
  const treeItems: FileTreeItem[] = artifacts.map((a) => ({
    id: a.id,
    name: a.filename,
    path: a.filename,
    type: 'file' as const,
    language: getLanguageLabel(a.filename),
  }));

  const handleOpenFile = useCallback(
    (item: FileTreeItem) => {
      // Find the matching artifact for the callback
      const artifact = artifacts.find((a) => a.id === item.id);
      if (artifact) {
        onFileSelect(artifact);
      }
      // Also open in FileStore for tab management
      fileStore.openFile({
        id: item.id,
        name: item.name,
        path: item.path,
        language: item.language ?? 'plaintext',
        isDirty: false,
        content: null, // loaded lazily when editor mounts
        lastAccessed: Date.now(),
      });
    },
    [artifacts, onFileSelect, fileStore]
  );

  const { flattenedItems, selectedId, setSelectedId, toggleExpand, handleKeyDown } = useFileTree(
    '',
    '',
    treeItems,
    handleOpenFile
  );

  if (artifacts.length === 0) {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center gap-2 p-6 text-center',
          className
        )}
      >
        <h3 className="text-sm font-medium text-foreground">No files yet</h3>
        <p className="text-xs text-muted-foreground">
          Upload files to the Artifacts section to browse and edit them here.
        </p>
      </div>
    );
  }

  return (
    <div
      role="tree"
      className={cn('flex h-full flex-col bg-muted/30', className)}
      onKeyDown={handleKeyDown as unknown as React.KeyboardEventHandler}
      tabIndex={0}
    >
      {/* Section header */}
      <div className="flex h-8 shrink-0 items-center px-4">
        <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Files
        </span>
      </div>

      {/* Virtualized tree */}
      <ScrollArea className="flex-1">
        <Virtuoso
          totalCount={flattenedItems.length}
          itemContent={(index) => {
            const item = flattenedItems[index]!;
            return (
              <FileTreeNode
                key={item.id}
                item={item}
                isSelected={selectedId === item.id}
                onSelect={() => setSelectedId(item.id)}
                onToggle={() => toggleExpand(item.id)}
                onOpen={handleOpenFile}
              />
            );
          }}
          style={{ height: '100%' }}
        />
      </ScrollArea>
    </div>
  );
});

'use client';

import { useCallback } from 'react';
import { observer } from 'mobx-react-lite';
import { Virtuoso } from 'react-virtuoso';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useFileStore } from '@/stores/RootStore';
import { useFileTree, type FileTreeItem } from '../hooks/useFileTree';
import { FileTreeNode } from './FileTreeNode';
import { cn } from '@/lib/utils';

interface FileTreeProps {
  items: FileTreeItem[];
  className?: string;
}

export const FileTree = observer(function FileTree({ items, className }: FileTreeProps) {
  const fileStore = useFileStore();

  const handleOpenFile = useCallback(
    (item: FileTreeItem) => {
      fileStore.openFile({
        id: item.id,
        name: item.name,
        path: item.path,
        source: item.source,
        language: item.language ?? 'plaintext',
        content: '',
        isReadOnly: item.source === 'remote',
      });
    },
    [fileStore]
  );

  const { flattenedItems, selectedId, setSelectedId, toggleExpand, handleKeyDown } = useFileTree(
    items,
    handleOpenFile
  );

  if (items.length === 0) {
    return (
      <div
        className={cn('flex flex-col items-center justify-center gap-2 p-6 text-center', className)}
      >
        <h3 className="text-sm font-medium text-foreground">No files yet</h3>
        <p className="text-xs text-muted-foreground">
          Open a project folder or create a new note to get started.
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

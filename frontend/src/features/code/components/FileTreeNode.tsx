'use client';

import { memo, useCallback } from 'react';
import {
  ChevronRight,
  File,
  FileCode,
  FileImage,
  FileJson,
  FileText,
  FileType,
  Folder,
  FolderOpen,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { FileTreeItem, FlattenedFileTreeItem } from '../hooks/useFileTree';
import { cn } from '@/lib/utils';

/** Render icon for a file based on extension. Static component for React 19 compliance. */
function FileIconForName({ name }: { name: string }) {
  const ext = name.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'ts':
    case 'tsx':
    case 'js':
    case 'jsx':
    case 'mjs':
    case 'cjs':
      return <FileCode className="h-4 w-4 shrink-0 text-muted-foreground" />;
    case 'md':
    case 'mdx':
      return <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />;
    case 'json':
    case 'jsonc':
      return <FileJson className="h-4 w-4 shrink-0 text-muted-foreground" />;
    case 'css':
    case 'scss':
    case 'less':
      return <FileType className="h-4 w-4 shrink-0 text-muted-foreground" />;
    case 'png':
    case 'jpg':
    case 'jpeg':
    case 'svg':
    case 'gif':
    case 'webp':
      return <FileImage className="h-4 w-4 shrink-0 text-muted-foreground" />;
    default:
      return <File className="h-4 w-4 shrink-0 text-muted-foreground" />;
  }
}

interface FileTreeNodeProps {
  item: FlattenedFileTreeItem;
  isSelected: boolean;
  onSelect: () => void;
  onToggle: () => void;
  onOpen: (item: FileTreeItem) => void;
}

export const FileTreeNode = memo(function FileTreeNode({
  item,
  isSelected,
  onSelect,
  onToggle,
  onOpen,
}: FileTreeNodeProps) {
  const handleClick = useCallback(() => {
    onSelect();
    if (item.type === 'directory') {
      onToggle();
    } else {
      onOpen(item);
    }
  }, [item, onSelect, onToggle, onOpen]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleClick();
      }
    },
    [handleClick]
  );

  const handleCopyPath = useCallback(() => {
    void navigator.clipboard.writeText(item.path);
  }, [item.path]);

  return (
    <DropdownMenu>
      <div
        role="treeitem"
        aria-expanded={item.type === 'directory' ? item.isExpanded : undefined}
        aria-selected={isSelected}
        tabIndex={isSelected ? 0 : -1}
        className={cn(
          'flex h-[28px] cursor-pointer select-none items-center gap-1.5 pr-2 text-sm min-w-0',
          'transition-colors duration-100',
          isSelected
            ? 'border-l-2 border-primary bg-background/80'
            : 'border-l-2 border-transparent hover:bg-muted/50'
        )}
        style={{ paddingLeft: item.depth * 16 + 8 }}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
      >
        {/* Chevron for directories */}
        {item.type === 'directory' ? (
          <ChevronRight
            className={cn(
              'h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-150 ease-out',
              item.isExpanded && 'rotate-90'
            )}
          />
        ) : (
          <span className="w-4 shrink-0" aria-hidden="true" />
        )}

        {/* Icon */}
        {item.type === 'directory' ? (
          item.isExpanded ? (
            <FolderOpen className="h-4 w-4 shrink-0 text-muted-foreground" />
          ) : (
            <Folder className="h-4 w-4 shrink-0 text-muted-foreground" />
          )
        ) : (
          <FileIconForName name={item.name} />
        )}

        {/* Name */}
        <DropdownMenuTrigger asChild>
          <span
            className="truncate min-w-0 flex-1"
            onContextMenu={(e) => {
              e.preventDefault();
              onSelect();
            }}
          >
            {item.name}
          </span>
        </DropdownMenuTrigger>
      </div>

      <DropdownMenuContent align="start" className="w-48">
        <DropdownMenuItem
          onSelect={() => {
            if (item.type === 'file') {
              onOpen(item);
            } else {
              onToggle();
            }
          }}
        >
          Open
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={handleCopyPath}>Copy Path</DropdownMenuItem>
        <DropdownMenuItem disabled>Rename</DropdownMenuItem>
        <DropdownMenuItem disabled>Delete</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
});

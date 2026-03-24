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
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { FileTreeItem, FlattenedFileTreeItem } from '../hooks/useFileTree';
import { cn } from '@/lib/utils';

function isTauri(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}

/** Render icon for a file based on extension. Defined outside component for React 19 static-components rule. */
function FileIconForName({ name }: { name: string }) {
  const ext = name.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'ts':
    case 'tsx':
    case 'js':
    case 'jsx':
      return <FileCode className="h-4 w-4 shrink-0 text-muted-foreground" />;
    case 'md':
    case 'mdx':
      return <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />;
    case 'json':
      return <FileJson className="h-4 w-4 shrink-0 text-muted-foreground" />;
    case 'css':
    case 'scss':
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

  const handleCopyPath = useCallback(() => {
    void navigator.clipboard.writeText(item.path);
  }, [item.path]);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <div
          role="treeitem"
          aria-expanded={item.type === 'directory' ? item.isExpanded : undefined}
          aria-selected={isSelected}
          tabIndex={isSelected ? 0 : -1}
          className={cn(
            'flex h-[28px] cursor-pointer select-none items-center gap-1 pr-2 text-sm',
            'transition-colors duration-100',
            isSelected
              ? 'border-l-2 border-primary bg-background/80'
              : 'border-l-2 border-transparent hover:bg-muted/50'
          )}
          style={{ paddingLeft: item.depth * 16 + 4 }}
          onClick={handleClick}
          onContextMenu={(_e) => {
            // Radix DropdownMenu will handle right-click via the trigger
            onSelect();
          }}
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
            <span className="w-4 shrink-0" /> // spacer for alignment
          )}

          {/* File icon */}
          {item.type !== 'directory' && <FileIconForName name={item.name} />}
          {item.type === 'directory' && (
            <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
          )}

          {/* Name */}
          <span className="truncate">{item.name}</span>
        </div>
      </DropdownMenuTrigger>

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
        {isTauri() && <DropdownMenuItem>Reveal in Finder</DropdownMenuItem>}
      </DropdownMenuContent>
    </DropdownMenu>
  );
});

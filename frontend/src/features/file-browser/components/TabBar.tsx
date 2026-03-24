'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { X, MoreHorizontal } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { useFileStore } from '@/stores/RootStore';
import type { OpenFile } from '@/features/editor/types';
import { cn } from '@/lib/utils';

interface TabItemProps {
  file: OpenFile;
  isActive: boolean;
  onActivate: () => void;
  onClose: () => void;
}

function TabItem({ file, isActive, onActivate, onClose }: TabItemProps) {
  const handleAuxClick = useCallback(
    (e: React.MouseEvent) => {
      // Middle-click (button === 1) closes the tab
      if (e.button === 1) {
        e.preventDefault();
        onClose();
      }
    },
    [onClose]
  );

  const handleCloseClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onClose();
    },
    [onClose]
  );

  return (
    <div
      role="tab"
      aria-selected={isActive}
      className={cn(
        'group relative flex shrink-0 cursor-pointer select-none items-center gap-1.5 px-3 text-sm',
        'animate-in fade-in slide-in-from-left-2 duration-150 ease-out',
        isActive
          ? 'border-b-2 border-primary text-foreground'
          : 'border-b-2 border-transparent text-muted-foreground hover:text-foreground'
      )}
      onClick={onActivate}
      onAuxClick={handleAuxClick}
    >
      {/* Dirty indicator */}
      {file.isDirty && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="h-1.5 w-1.5 shrink-0 animate-in zoom-in-50 rounded-full bg-primary duration-150" />
            </TooltipTrigger>
            <TooltipContent>Unsaved changes</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}

      <span className="truncate">{file.name}</span>

      {/* Close button - visible on hover */}
      <button
        type="button"
        className="invisible shrink-0 rounded p-0.5 hover:bg-muted group-hover:visible"
        onClick={handleCloseClick}
        aria-label={`Close ${file.name}`}
      >
        <X className="h-3 w-3" />
      </button>
    </div>
  );
}

export const TabBar = observer(function TabBar() {
  const fileStore = useFileStore();
  const containerRef = useRef<HTMLDivElement>(null);
  const [overflowTabs, setOverflowTabs] = useState<OpenFile[]>([]);

  const tabs = fileStore.tabs;
  const activeFileId = fileStore.activeFileId;

  // Detect overflow
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const checkOverflow = () => {
      const children = Array.from(container.children) as HTMLElement[];
      const hidden: OpenFile[] = [];
      for (let i = 0; i < children.length; i++) {
        const child = children[i]!;
        if (child.dataset.tabId && child.offsetLeft + child.offsetWidth > container.clientWidth) {
          const tab = tabs.find((t) => t.id === child.dataset.tabId);
          if (tab) hidden.push(tab);
        }
      }
      setOverflowTabs(hidden);
    };

    const observer = new ResizeObserver(checkOverflow);
    observer.observe(container);
    checkOverflow();

    return () => observer.disconnect();
  }, [tabs]);

  if (tabs.length === 0) return null;

  return (
    <div className="flex h-[36px] shrink-0 items-stretch border-b border-border bg-muted/30">
      <div
        role="tablist"
        ref={containerRef}
        className="flex flex-1 items-stretch gap-2 overflow-hidden"
      >
        {tabs.map((file) => (
          <div key={file.id} data-tab-id={file.id}>
            <TabItem
              file={file}
              isActive={activeFileId === file.id}
              onActivate={() => fileStore.openFile(file)}
              onClose={() => fileStore.closeFile(file.id)}
            />
          </div>
        ))}
      </div>

      {/* Overflow menu */}
      {overflowTabs.length > 0 && (
        <Popover>
          <PopoverTrigger asChild>
            <button
              type="button"
              className="flex shrink-0 items-center px-2 text-muted-foreground hover:text-foreground"
              aria-label="Show more tabs"
            >
              <MoreHorizontal className="h-4 w-4" />
            </button>
          </PopoverTrigger>
          <PopoverContent align="end" className="w-56 p-1">
            {overflowTabs.map((file) => (
              <button
                key={file.id}
                type="button"
                className={cn(
                  'flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-muted',
                  activeFileId === file.id && 'bg-muted font-medium'
                )}
                onClick={() => fileStore.openFile(file)}
              >
                {file.isDirty && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />}
                <span className="truncate">{file.name}</span>
              </button>
            ))}
          </PopoverContent>
        </Popover>
      )}
    </div>
  );
});

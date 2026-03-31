'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { X, MoreHorizontal } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { useFileStore } from '@/stores/RootStore';
import type { OpenFile } from '../types';
import { cn } from '@/lib/utils';

// ─── Tab height CSS custom property ───────────────────────────────────────────
// --tab-height: 36px — matches Figma design spec

interface TabItemProps {
  file: OpenFile;
  isActive: boolean;
  onActivate: () => void;
  onClose: () => void;
}

function TabItem({ file, isActive, onActivate, onClose }: TabItemProps) {
  const confirmAndClose = useCallback(() => {
    if (file.isDirty) {
      const confirmed = window.confirm(
        `"${file.name}" has unsaved changes. Close without saving?`
      );
      if (!confirmed) return;
    }
    onClose();
  }, [file.isDirty, file.name, onClose]);

  const handleAuxClick = useCallback(
    (e: React.MouseEvent) => {
      // Middle-click (button === 1) closes the tab
      if (e.button === 1) {
        e.preventDefault();
        confirmAndClose();
      }
    },
    [confirmAndClose]
  );

  const handleCloseClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      confirmAndClose();
    },
    [confirmAndClose]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        if (e.key === ' ') e.preventDefault(); // Prevent scroll
        onActivate();
      }
    },
    [onActivate]
  );

  return (
    <div
      role="tab"
      aria-selected={isActive}
      tabIndex={isActive ? 0 : -1}
      className={cn(
        'group relative flex shrink-0 cursor-pointer select-none items-center gap-1.5 px-3 text-sm',
        'animate-in fade-in slide-in-from-left-2 duration-150 ease-out',
        'h-[var(--tab-height,36px)]',
        isActive
          ? 'border-b-2 border-primary text-foreground'
          : 'border-b-2 border-transparent text-muted-foreground hover:text-foreground'
      )}
      onClick={onActivate}
      onAuxClick={handleAuxClick}
      onKeyDown={handleKeyDown}
    >
      {/* Dirty indicator dot */}
      {file.isDirty && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <span
                className="h-1.5 w-1.5 shrink-0 animate-in zoom-in-50 rounded-full bg-primary duration-150"
                data-testid="dirty-indicator"
              />
            </TooltipTrigger>
            <TooltipContent>Unsaved changes</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}

      <span className="max-w-[120px] truncate">{file.name}</span>

      {/* Close button — visible on hover */}
      <button
        type="button"
        className="invisible shrink-0 rounded p-0.5 hover:bg-muted group-hover:visible focus:visible group-focus-within:visible"
        onClick={handleCloseClick}
        aria-label={`Close ${file.name}`}
      >
        <X className="h-3 w-3" />
      </button>
    </div>
  );
}

// ─── TabBar ────────────────────────────────────────────────────────────────────

/**
 * TabBar — progressive horizontal file tab strip.
 *
 * Progressive disclosure: returns null when no files are open.
 * Uses ResizeObserver to detect overflow and show "..." dropdown for hidden tabs.
 * Height: 36px (--tab-height CSS custom property).
 */
export const TabBar = observer(function TabBar() {
  const fileStore = useFileStore();
  const containerRef = useRef<HTMLDivElement>(null);
  const [overflowTabs, setOverflowTabs] = useState<OpenFile[]>([]);

  // Derive ordered tabs from openFiles map using tabOrder
  const tabs = fileStore.tabOrder.map((id) => fileStore.openFiles.get(id)).filter((f): f is OpenFile => f !== undefined);
  const activeFileId = fileStore.activeFileId;

  // Keep a ref to tabs so the ResizeObserver callback reads the latest without re-subscribing
  const tabsRef = useRef(tabs);
  tabsRef.current = tabs;

  // Detect overflow with ResizeObserver — re-attach only when tab count changes
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const checkOverflow = () => {
      const currentTabs = tabsRef.current;
      const children = Array.from(container.children) as HTMLElement[];
      const hidden: OpenFile[] = [];
      for (const child of children) {
        if (child.dataset.tabId && child.offsetLeft + child.offsetWidth > container.clientWidth) {
          const tab = currentTabs.find((t) => t.id === child.dataset.tabId);
          if (tab) hidden.push(tab);
        }
      }
      setOverflowTabs(hidden);
    };

    const observer = new ResizeObserver(checkOverflow);
    observer.observe(container);
    checkOverflow();

    return () => observer.disconnect();
  }, [tabs.length, activeFileId]);

  // Progressive disclosure: hidden when no tabs are open
  if (tabs.length === 0) return null;

  return (
    <div
      className="flex shrink-0 items-stretch border-b border-border bg-muted/30"
      style={{ height: 'var(--tab-height, 36px)' }}
    >
      <div
        role="tablist"
        ref={containerRef}
        className="flex flex-1 items-stretch gap-0 overflow-hidden"
      >
        {tabs.map((file) => (
          <div key={file.id} data-tab-id={file.id}>
            <TabItem
              file={file}
              isActive={activeFileId === file.id}
              onActivate={() => fileStore.setActiveFile(file.id)}
              onClose={() => fileStore.closeFile(file.id)}
            />
          </div>
        ))}
      </div>

      {/* Overflow menu — shown when tabs overflow container width */}
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
                onClick={() => fileStore.setActiveFile(file.id)}
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

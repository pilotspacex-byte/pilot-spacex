'use client';

import { useCallback } from 'react';
import { observer } from 'mobx-react-lite';
import { X, Pin, ChevronLeft, ChevronRight } from 'lucide-react';
import { useArtifactPanelStore } from '@/stores';
import { cn } from '@/lib/utils';

export const ArtifactTabBar = observer(function ArtifactTabBar() {
  const artifactPanel = useArtifactPanelStore();
  const { openTabs, activeTabId } = artifactPanel;

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, index: number) => {
      let nextIndex: number | null = null;

      if (e.key === 'ArrowRight') {
        nextIndex = (index + 1) % openTabs.length;
      } else if (e.key === 'ArrowLeft') {
        nextIndex = (index - 1 + openTabs.length) % openTabs.length;
      } else if (e.key === 'Home') {
        nextIndex = 0;
      } else if (e.key === 'End') {
        nextIndex = openTabs.length - 1;
      }

      if (nextIndex !== null) {
        e.preventDefault();
        const tab = openTabs[nextIndex];
        if (tab) {
          artifactPanel.setActiveTab(tab.id);
          // Focus the tab element
          const tabEl = e.currentTarget.parentElement?.children[nextIndex] as HTMLElement;
          tabEl?.focus();
        }
      }
    },
    [openTabs, artifactPanel]
  );

  if (openTabs.length === 0) return null;

  return (
    <div className="flex h-10 items-center border-b border-border px-2 gap-1">
      {/* Back/forward navigation */}
      <div className="flex items-center gap-0.5 shrink-0 mr-1">
        <button
          type="button"
          disabled={!artifactPanel.canGoBack}
          aria-label="Go back"
          className="inline-flex h-6 w-6 items-center justify-center rounded-sm text-muted-foreground hover:text-foreground hover:bg-accent/50 disabled:opacity-30 disabled:pointer-events-none transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          onClick={() => artifactPanel.goBack()}
        >
          <ChevronLeft className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          disabled={!artifactPanel.canGoForward}
          aria-label="Go forward"
          className="inline-flex h-6 w-6 items-center justify-center rounded-sm text-muted-foreground hover:text-foreground hover:bg-accent/50 disabled:opacity-30 disabled:pointer-events-none transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          onClick={() => artifactPanel.goForward()}
        >
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Tabs */}
      <div role="tablist" aria-label="Open artifacts" className="flex items-center gap-1 overflow-x-auto flex-1">
      {openTabs.map((tab, index) => {
        const isActive = tab.id === activeTabId;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            tabIndex={isActive ? 0 : -1}
            className={cn(
              'group flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              isActive
                ? 'bg-accent text-accent-foreground font-medium'
                : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
            )}
            onClick={() => artifactPanel.setActiveTab(tab.id)}
            onKeyDown={(e) => handleKeyDown(e, index)}
          >
            <span className="truncate max-w-[120px]">{tab.title}</span>
            {tab.isPinned && <Pin className="h-2.5 w-2.5 text-muted-foreground" />}
            <button
              type="button"
              tabIndex={0}
              aria-label={`Close ${tab.title}`}
              className={cn(
                'inline-flex items-center justify-center rounded-sm',
                'h-5 w-5 min-h-[20px] min-w-[20px]',
                'opacity-0 group-hover:opacity-100 group-focus-within:opacity-100',
                'focus:opacity-100',
                'transition-opacity hover:bg-accent-foreground/10',
                'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring'
              )}
              onClick={(e) => {
                e.stopPropagation();
                artifactPanel.closeTab(tab.id);
              }}
            >
              <X className="h-3 w-3" />
            </button>
          </button>
        );
      })}
      </div>
    </div>
  );
});

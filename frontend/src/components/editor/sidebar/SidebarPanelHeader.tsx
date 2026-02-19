'use client';

import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { SidebarPanelId } from './useSidebarPanel';

export interface SidebarTab {
  id: SidebarPanelId;
  label: string;
  icon?: React.ReactNode;
  /** When true, shows a "Coming Soon" badge and disables the tab. */
  comingSoon?: boolean;
  /** When true, disables the tab without a coming soon label. */
  disabled?: boolean;
}

export interface SidebarPanelHeaderProps {
  title: string;
  tabs?: SidebarTab[];
  activePanel: SidebarPanelId | null;
  onTabChange: (panel: SidebarPanelId) => void;
  onClose: () => void;
  className?: string;
}

export function SidebarPanelHeader({
  title,
  tabs,
  activePanel,
  onTabChange,
  onClose,
  className,
}: SidebarPanelHeaderProps) {
  // COL-M6: roving tabindex — Arrow keys move focus between tabs
  function handleTablistKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
    if (!tabs || tabs.length === 0) return;
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    e.preventDefault();

    // Only navigate among enabled tabs
    const enabledTabs = tabs.filter((t) => !t.comingSoon && !t.disabled);
    const currentIndex = enabledTabs.findIndex((t) => t.id === activePanel);
    const total = enabledTabs.length;
    if (total === 0) return;
    let nextIndex: number;

    if (e.key === 'ArrowRight') {
      nextIndex = currentIndex === -1 ? 0 : (currentIndex + 1) % total;
    } else {
      nextIndex = currentIndex === -1 ? total - 1 : (currentIndex - 1 + total) % total;
    }

    const nextTab = enabledTabs[nextIndex];
    if (nextTab) {
      onTabChange(nextTab.id);
      // Move DOM focus to the newly selected tab button
      const btn = document.getElementById(`sidebar-tab-${nextTab.id}`);
      btn?.focus();
    }
  }

  return (
    <div
      className={cn('flex flex-col border-b border-border bg-background', className)}
      data-testid="sidebar-panel-header"
    >
      {/* Title row */}
      <div className="flex items-center justify-between px-3 py-2.5">
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 shrink-0 text-muted-foreground hover:text-foreground"
          onClick={onClose}
          aria-label="Close sidebar panel"
          data-testid="sidebar-close-button"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>

      {/* Tab navigation */}
      {tabs && tabs.length > 0 && (
        <div
          className="flex gap-0.5 px-2 pb-0"
          role="tablist"
          aria-label={`${title} panel tabs`}
          onKeyDown={handleTablistKeyDown}
        >
          {tabs.map((tab) => {
            const isUnavailable = tab.comingSoon || tab.disabled;
            return (
              <button
                key={tab.id}
                role="tab"
                aria-selected={activePanel === tab.id}
                aria-controls={`sidebar-panel-content-${tab.id}`}
                id={`sidebar-tab-${tab.id}`}
                tabIndex={isUnavailable ? -1 : activePanel === tab.id ? 0 : -1}
                disabled={isUnavailable}
                onClick={() => {
                  if (!isUnavailable) onTabChange(tab.id);
                }}
                title={tab.comingSoon ? `${tab.label} — Coming Soon` : undefined}
                aria-disabled={isUnavailable}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-t transition-colors',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
                  isUnavailable
                    ? 'opacity-40 cursor-not-allowed text-muted-foreground'
                    : activePanel === tab.id
                      ? 'border-b-2 border-primary text-primary bg-primary/5'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'
                )}
                data-testid={`sidebar-tab-${tab.id}`}
              >
                {tab.icon}
                {tab.label}
                {tab.comingSoon && (
                  <span className="ml-1 rounded-full bg-muted px-1 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-muted-foreground">
                    Soon
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

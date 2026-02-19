'use client';

import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { SidebarPanelId } from './useSidebarPanel';

export interface SidebarTab {
  id: SidebarPanelId;
  label: string;
  icon?: React.ReactNode;
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
        <div className="flex gap-0.5 px-2 pb-0" role="tablist" aria-label={`${title} panel tabs`}>
          {tabs.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activePanel === tab.id}
              aria-controls={`sidebar-panel-content-${tab.id}`}
              id={`sidebar-tab-${tab.id}`}
              onClick={() => onTabChange(tab.id)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-t transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
                activePanel === tab.id
                  ? 'border-b-2 border-primary text-primary bg-primary/5'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'
              )}
              data-testid={`sidebar-tab-${tab.id}`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

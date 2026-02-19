'use client';

import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import type { SidebarPanelId } from './useSidebarPanel';

export interface SidebarPanelContentProps {
  activePanel: SidebarPanelId | null;
  children: React.ReactNode;
  className?: string;
}

export function SidebarPanelContent({
  activePanel,
  children,
  className,
}: SidebarPanelContentProps) {
  return (
    <ScrollArea
      className={cn('flex-1 overflow-auto', className)}
      role="tabpanel"
      id={activePanel ? `sidebar-panel-content-${activePanel}` : undefined}
      aria-labelledby={activePanel ? `sidebar-tab-${activePanel}` : undefined}
      data-testid="sidebar-panel-content"
    >
      <div className="h-full">{children}</div>
    </ScrollArea>
  );
}

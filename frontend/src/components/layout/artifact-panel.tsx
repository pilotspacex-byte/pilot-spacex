'use client';

import { useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { reaction } from 'mobx';
import { Maximize2, Minimize2 } from 'lucide-react';
import { useArtifactPanelStore, useUIStore } from '@/stores';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { ArtifactTabBar } from './artifact-tab-bar';
import type { ReactNode } from 'react';

interface ArtifactPanelProps {
  children?: ReactNode;
}

export const ArtifactPanel = observer(function ArtifactPanel({ children }: ArtifactPanelProps) {
  const artifactPanel = useArtifactPanelStore();
  const uiStore = useUIStore();

  // Auto-transition layoutMode when tabs open/close
  useEffect(() => {
    const disposer = reaction(
      () => artifactPanel.hasOpenTabs,
      (hasTabs) => {
        if (hasTabs && uiStore.layoutMode === 'chat-first') {
          uiStore.setLayoutMode('chat-artifact');
        } else if (!hasTabs && uiStore.layoutMode !== 'chat-first') {
          uiStore.setLayoutMode('chat-first');
        }
      }
    );
    return () => disposer();
  }, [artifactPanel, uiStore]);

  const isCanvasFirst = uiStore.layoutMode === 'canvas-first';

  const handleToggleExpand = () => {
    if (isCanvasFirst) {
      uiStore.setLayoutMode('chat-artifact');
    } else {
      uiStore.setLayoutMode('canvas-first');
    }
  };

  return (
    <div className="flex h-full flex-col bg-background border-l border-border">
      {/* Tab bar + expand control */}
      <div className="flex items-center">
        <div className="flex-1 overflow-hidden">
          <ArtifactTabBar />
        </div>
        {artifactPanel.hasOpenTabs && (
          <div className="shrink-0 px-2 border-b border-border h-10 flex items-center">
            <Tooltip delayDuration={0}>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={handleToggleExpand}
                >
                  {isCanvasFirst ? (
                    <Minimize2 className="h-3.5 w-3.5" />
                  ) : (
                    <Maximize2 className="h-3.5 w-3.5" />
                  )}
                  <span className="sr-only">
                    {isCanvasFirst ? 'Restore split view' : 'Expand to full width'}
                  </span>
                </Button>
              </TooltipTrigger>
              <TooltipContent side="left">
                {isCanvasFirst ? 'Restore split view' : 'Expand to full width'}
              </TooltipContent>
            </Tooltip>
          </div>
        )}
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-auto">
        {children ? (
          <div className="h-full">{children}</div>
        ) : artifactPanel.hasOpenTabs ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-muted-foreground">
              {artifactPanel.activeTab?.title ?? 'Loading...'}
            </p>
          </div>
        ) : (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-muted-foreground">No artifacts open</p>
          </div>
        )}
      </div>
    </div>
  );
});

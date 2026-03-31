'use client';

import { useCallback } from 'react';
import { observer } from 'mobx-react-lite';
import { ChevronRight, GitCompareArrows } from 'lucide-react';
import { useFileStore } from '@/stores/RootStore';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

/**
 * BreadcrumbBar — shows the active file's path above the editor.
 *
 * Splits the active file path on "/" and renders clickable segments for
 * lateral navigation. The last segment (current filename) is non-clickable.
 * When the active file has unsaved changes, a "View Diff" button appears.
 * Hidden on mobile via `hidden md:flex`.
 * Height: 36px.
 */
export const BreadcrumbBar = observer(function BreadcrumbBar() {
  const fileStore = useFileStore();
  const activeFile = fileStore.activeFile;

  const handleViewDiff = useCallback(() => {
    if (!activeFile) return;
    window.dispatchEvent(
      new CustomEvent('file-editor:view-diff', {
        detail: {
          fileId: activeFile.id,
          filePath: activeFile.path,
          language: activeFile.language,
          originalContent: activeFile.originalContent ?? '',
          modifiedContent: activeFile.content ?? '',
        },
      })
    );
  }, [activeFile]);

  if (!activeFile) return null;

  const segments = activeFile.path.split('/').filter(Boolean);
  const hasDiff = activeFile.isDirty && activeFile.originalContent != null && activeFile.content != null;

  return (
    <div className="hidden h-9 items-center justify-between overflow-x-auto border-b border-border bg-background/50 px-3 md:flex">
      {/* Path segments */}
      <div className="flex items-center min-w-0">
        {segments.map((segment, index) => {
          const isLast = index === segments.length - 1;
          const segmentPath = segments.slice(0, index + 1).join('/');

          return (
            <span key={segmentPath} className="flex items-center">
              {index > 0 && (
                <ChevronRight className="mx-1 h-3.5 w-3.5 shrink-0 text-muted-foreground/50" />
              )}
              <span
                className={cn(
                  'rounded px-1 py-0.5 text-xs',
                  isLast
                    ? 'font-medium text-foreground'
                    : 'text-muted-foreground'
                )}
                title={isLast ? undefined : segmentPath}
              >
                {segment}
              </span>
            </span>
          );
        })}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 shrink-0 ml-2">
        {hasDiff && (
          <TooltipProvider delayDuration={300}>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={handleViewDiff}
                  className="flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                  aria-label="View unsaved changes diff"
                >
                  <GitCompareArrows className="h-3.5 w-3.5" />
                  <span>Diff</span>
                </button>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="text-xs">
                View unsaved changes (Cmd+Shift+D)
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>
    </div>
  );
});

'use client';

import { observer } from 'mobx-react-lite';
import { ChevronRight } from 'lucide-react';
import { useFileStore } from '@/stores/RootStore';
import { cn } from '@/lib/utils';

/**
 * BreadcrumbBar — shows the active file's path above the editor.
 *
 * Splits the active file path on "/" and renders clickable segments for
 * lateral navigation. The last segment (current filename) is non-clickable.
 * Hidden on mobile via `hidden md:flex`.
 * Height: 36px.
 */
export const BreadcrumbBar = observer(function BreadcrumbBar() {
  const fileStore = useFileStore();
  const activeFile = fileStore.activeFile;

  if (!activeFile) return null;

  const segments = activeFile.path.split('/').filter(Boolean);

  return (
    <div className="hidden h-9 items-center overflow-x-auto border-b border-border bg-background/50 px-3 md:flex">
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
                  : 'cursor-pointer text-muted-foreground hover:bg-muted hover:text-foreground transition-colors'
              )}
              title={isLast ? undefined : segmentPath}
            >
              {segment}
            </span>
          </span>
        );
      })}
    </div>
  );
});

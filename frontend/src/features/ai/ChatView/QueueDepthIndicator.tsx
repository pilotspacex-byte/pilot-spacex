/**
 * QueueDepthIndicator — sticky bar showing running/queued skill execution state.
 *
 * Only shown when at least 1 skill is running or queued.
 * Lives at the top of MessageList (below ChatHeader).
 *
 * Spec: specs/015-ai-workforce-platform/ui-design.md §6
 * T-060
 */
'use client';

import { Activity, AlertTriangle } from 'lucide-react';
import { observer } from 'mobx-react-lite';
import { cn } from '@/lib/utils';
import type { PilotSpaceStore } from '@/stores/ai/PilotSpaceStore';

interface QueueDepthIndicatorProps {
  store: PilotSpaceStore;
  className?: string;
}

export const QueueDepthIndicator = observer<QueueDepthIndicatorProps>(function QueueDepthIndicator({
  store,
  className,
}) {
  const { runningCount, queuedCount, maxConcurrent } = store.skillQueue;
  const isQueueFull = runningCount >= maxConcurrent;

  // Hidden when idle
  if (runningCount === 0 && queuedCount === 0) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      aria-label={`Skill execution queue: ${runningCount} running, ${queuedCount} queued`}
      className={cn(
        'sticky top-0 z-10 flex items-center gap-3 px-4 py-2',
        'border-b bg-background-subtle text-xs',
        isQueueFull
          ? 'bg-amber-50 border-amber-200 dark:bg-amber-950/30 dark:border-amber-800'
          : '',
        className
      )}
    >
      <Activity className="h-3.5 w-3.5 text-muted-foreground shrink-0" aria-hidden="true" />

      {/* Running count */}
      {runningCount > 0 && (
        <div className="flex items-center gap-1.5">
          <span
            className="h-1.5 w-1.5 rounded-full bg-primary inline-block animate-pulse"
            aria-hidden="true"
          />
          <span className="font-medium text-primary tabular-nums">{runningCount} running</span>
        </div>
      )}

      {/* Separator */}
      {runningCount > 0 && queuedCount > 0 && (
        <div className="h-4 w-px bg-border" aria-hidden="true" />
      )}

      {/* Queued count */}
      {queuedCount > 0 && (
        <div className="flex items-center gap-1.5">
          <span
            className="h-1.5 w-1.5 rounded-full bg-muted-foreground inline-block"
            aria-hidden="true"
          />
          <span className="font-medium text-muted-foreground tabular-nums">
            {queuedCount} queued
          </span>
        </div>
      )}

      {/* Max label — decorative, screen readers skip it */}
      <span className="text-muted-foreground ml-auto tabular-nums" aria-hidden="true">
        max {maxConcurrent}
      </span>

      {/* Queue full warning */}
      <div aria-live="assertive" role="alert">
        {isQueueFull && (
          <div className="flex items-center gap-1 text-amber-600 dark:text-amber-400">
            <AlertTriangle className="h-3 w-3" aria-hidden="true" />
            <span>Queue full — new skills will wait</span>
          </div>
        )}
      </div>
    </div>
  );
});

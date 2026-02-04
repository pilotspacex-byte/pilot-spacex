/**
 * ToolStepTimeline - Vertical step timeline for messages with 3+ tool calls.
 *
 * Renders a numbered vertical timeline with status-based circle indicators,
 * tool display names, and duration badges. Returns null for fewer than 3 tools.
 *
 * @module features/ai/ChatView/MessageList/ToolStepTimeline
 */

import { memo, useState } from 'react';
import { Check, X, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getToolDisplayName } from '@/features/ai/ChatView/constants';
import { useElapsedTime } from '@/hooks/useElapsedTime';
import type { ToolCall } from '@/stores/ai/types/conversation';

interface ToolStepTimelineProps {
  toolCalls: ToolCall[];
  className?: string;
}

/** Format duration in ms to a human-readable string (e.g., "0.8s", "2.1s"). */
function formatDuration(ms: number): string {
  const seconds = ms / 1000;
  if (seconds < 10) return `${seconds.toFixed(1)}s`;
  return `${Math.floor(seconds)}s`;
}

/**
 * Determine the effective display status for a tool call step.
 *
 * The ToolCall type uses 'pending' for both waiting and actively running tools.
 * The first pending tool in sequence is considered "running"; subsequent pending
 * tools are "waiting" (hollow circle).
 */
type StepStatus = 'completed' | 'failed' | 'running' | 'waiting';

function resolveStepStatuses(toolCalls: ToolCall[]): StepStatus[] {
  let firstPendingSeen = false;

  return toolCalls.map((tc) => {
    if (tc.status === 'completed') return 'completed';
    if (tc.status === 'failed') return 'failed';

    // First pending tool is actively running
    if (!firstPendingSeen) {
      firstPendingSeen = true;
      return 'running';
    }

    return 'waiting';
  });
}

/** Single step row with circle indicator, name, and duration. */
const StepRow = memo<{
  toolCall: ToolCall;
  stepStatus: StepStatus;
  isLast: boolean;
}>(({ toolCall, stepStatus, isLast }) => {
  const displayName = getToolDisplayName(toolCall.name);
  const isRunning = stepStatus === 'running';

  // Lazy state initializer avoids impure Date.now() call during render (react-hooks/purity)
  const [startTime] = useState(() => Date.now());
  const elapsed = useElapsedTime(isRunning ? startTime : null, isRunning);

  const ariaStatus = stepStatus === 'waiting' ? 'pending' : stepStatus;

  return (
    <li aria-label={`${displayName} — ${ariaStatus}`}>
      <div className="flex items-start gap-3">
        {/* Circle + vertical connector */}
        <div className="flex flex-col items-center">
          {/* Status circle: 20px diameter */}
          <div
            className={cn(
              'flex h-5 w-5 shrink-0 items-center justify-center rounded-full',
              stepStatus === 'completed' && 'bg-primary',
              stepStatus === 'failed' && 'bg-destructive',
              stepStatus === 'running' && 'border-2 border-ai bg-ai',
              stepStatus === 'waiting' && 'border-2 border-muted-foreground bg-background'
            )}
          >
            {stepStatus === 'completed' && <Check className="h-2.5 w-2.5 text-white" />}
            {stepStatus === 'failed' && <X className="h-2.5 w-2.5 text-white" />}
            {stepStatus === 'running' && (
              <Loader2 className="h-2.5 w-2.5 animate-spin text-white" />
            )}
            {/* waiting: hollow circle, no icon */}
          </div>

          {/* Vertical connecting line (skip for last item) */}
          {!isLast && <div className="h-4 w-0 border-l-2 border-l-border-subtle" />}
        </div>

        {/* Tool name + duration */}
        <div className="flex min-w-0 flex-1 items-center gap-2 pt-px">
          <span className="truncate text-sm font-medium">{displayName}</span>

          {/* Duration badge */}
          {stepStatus === 'completed' && toolCall.durationMs != null && (
            <span className="font-mono text-xs tabular-nums text-muted-foreground">
              {formatDuration(toolCall.durationMs)}
            </span>
          )}
          {stepStatus === 'running' && (
            <span className="font-mono text-xs tabular-nums text-muted-foreground">{elapsed}</span>
          )}
        </div>
      </div>
    </li>
  );
});

StepRow.displayName = 'StepRow';

export const ToolStepTimeline = memo<ToolStepTimelineProps>(({ toolCalls, className }) => {
  if (toolCalls.length < 3) return null;

  const stepStatuses = resolveStepStatuses(toolCalls);

  return (
    <ol aria-label="Tool execution steps" className={cn('space-y-0', className)}>
      {toolCalls.map((toolCall, index) => (
        <StepRow
          key={toolCall.id}
          toolCall={toolCall}
          stepStatus={stepStatuses[index] ?? 'waiting'}
          isLast={index === toolCalls.length - 1}
        />
      ))}
    </ol>
  );
});

ToolStepTimeline.displayName = 'ToolStepTimeline';

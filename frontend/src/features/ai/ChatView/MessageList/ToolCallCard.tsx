/**
 * ToolCallCard - Rich status card for individual tool call execution.
 *
 * Displays human-readable tool name, status icon with color coding,
 * elapsed/completed duration, collapsible input/output detail,
 * partial input streaming indicator (G-09), and error messages.
 *
 * @module features/ai/ChatView/MessageList/ToolCallCard
 */

'use client';

import { useState } from 'react';
import { observer } from 'mobx-react-lite';
import { Loader2, CheckCircle2, XCircle, ChevronDown } from 'lucide-react';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { cn } from '@/lib/utils';
import { useElapsedTime } from '@/hooks/useElapsedTime';
import { getToolDisplayName } from '../constants';
import type { ToolCall } from '@/stores/ai/types/conversation';

interface ToolCallCardProps {
  toolCall: ToolCall;
  className?: string;
}

const STATUS_ICON_MAP = {
  pending: Loader2,
  completed: CheckCircle2,
  failed: XCircle,
} as const;

const STATUS_COLOR_MAP = {
  pending: 'text-ai',
  completed: 'text-primary',
  failed: 'text-destructive',
} as const;

const STATUS_LABEL_MAP = {
  pending: 'Pending',
  completed: 'Completed',
  failed: 'Failed',
} as const;

/** Format duration in milliseconds to a compact string (e.g., "0.8s", "2.1s") */
function formatDuration(ms: number): string {
  const seconds = ms / 1000;
  if (seconds < 10) {
    return `${seconds.toFixed(1)}s`;
  }
  return `${Math.floor(seconds)}s`;
}

export const ToolCallCard = observer<ToolCallCardProps>(({ toolCall, className }) => {
  const status = toolCall.status || 'pending';
  const displayName = getToolDisplayName(toolCall.name);
  const statusLabel = STATUS_LABEL_MAP[status] || 'Pending';

  const StatusIcon = STATUS_ICON_MAP[status] || Loader2;
  const statusColor = STATUS_COLOR_MAP[status] || 'text-ai';

  // Elapsed time: capture start time on mount via lazy state initializer (pure)
  const [startTime] = useState(() => Date.now());
  const isRunning = status === 'pending';
  const elapsed = useElapsedTime(startTime, isRunning);

  const [isOpen, setIsOpen] = useState(false);

  // Duration display
  const durationText = isRunning
    ? elapsed
    : status === 'completed' && toolCall.durationMs != null
      ? formatDuration(toolCall.durationMs)
      : null;

  const hasInput =
    (status === 'pending' && toolCall.partialInput) || Object.keys(toolCall.input).length > 0;
  const hasOutput = toolCall.output !== undefined;
  const hasDetail = hasInput || hasOutput;

  return (
    <div
      role="article"
      aria-label={`${displayName} — ${statusLabel}`}
      className={cn(
        'rounded-[10px] border border-border-subtle bg-background-subtle',
        'transition-shadow hover:shadow-warm-sm',
        className
      )}
    >
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <button
            type="button"
            className={cn(
              'flex w-full items-center gap-3 px-3 py-2.5 text-left',
              'transition-colors hover:bg-accent/30',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              'focus-visible:ring-offset-2 rounded-[10px]'
            )}
          >
            {/* Status icon */}
            <StatusIcon
              className={cn(
                'h-4 w-4 shrink-0',
                statusColor,
                status === 'pending' && 'animate-spin motion-reduce:animate-none'
              )}
              aria-hidden="true"
            />

            {/* Tool name + error */}
            <div className="flex-1 min-w-0">
              <span className="text-sm font-medium truncate block">{displayName}</span>
              {toolCall.errorMessage && (
                <p className="text-xs text-destructive mt-0.5 truncate">{toolCall.errorMessage}</p>
              )}
            </div>

            {/* Duration */}
            {durationText && (
              <span className="text-xs text-muted-foreground tabular-nums shrink-0">
                {durationText}
              </span>
            )}

            {/* Chevron */}
            {hasDetail && (
              <ChevronDown
                className={cn(
                  'h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform',
                  isOpen && 'rotate-180'
                )}
                aria-hidden="true"
              />
            )}
          </button>
        </CollapsibleTrigger>

        {hasDetail && (
          <CollapsibleContent>
            <div className="border-t border-border-subtle px-3 py-2.5 space-y-2.5">
              {/* Partial input while streaming (G-09) */}
              {status === 'pending' && toolCall.partialInput ? (
                <div className="space-y-1">
                  <span className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                    Input
                    <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-ai" />
                  </span>
                  <pre className="text-xs bg-muted/50 p-2 rounded-md overflow-x-auto opacity-60 font-mono">
                    {toolCall.partialInput}
                  </pre>
                </div>
              ) : Object.keys(toolCall.input).length > 0 ? (
                <div className="space-y-1">
                  <span className="text-xs font-medium text-muted-foreground">Input</span>
                  <pre className="text-xs bg-muted/50 p-2 rounded-md overflow-x-auto font-mono">
                    {JSON.stringify(toolCall.input, null, 2)}
                  </pre>
                </div>
              ) : null}

              {/* Output */}
              {hasOutput && (
                <div className="space-y-1">
                  <span className="text-xs font-medium text-muted-foreground">Output</span>
                  <pre className="text-xs bg-muted/50 p-2 rounded-md overflow-x-auto font-mono">
                    {typeof toolCall.output === 'string'
                      ? toolCall.output
                      : JSON.stringify(toolCall.output, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </CollapsibleContent>
        )}
      </Collapsible>
    </div>
  );
});

ToolCallCard.displayName = 'ToolCallCard';

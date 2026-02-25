/**
 * ReasoningGroup - Collapsible container for thinking + tool call blocks.
 *
 * Groups consecutive reasoning blocks (thinking, tool_use) into a single
 * collapsible section with a summary line, reducing visual clutter in
 * completed messages.
 *
 * Design: Single-line toggle like ThinkingBlock / ToolCallCard
 * Only used for completed (non-streaming) messages.
 *
 * @module features/ai/ChatView/MessageList/ReasoningGroup
 */

'use client';

import { memo, useState, useMemo } from 'react';
import { ChevronDown, Layers } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ReasoningGroupProps {
  /** Total number of reasoning steps (thinking + tool calls) */
  stepCount: number;
  /** Total duration across all steps in ms */
  totalDurationMs: number;
  /** The child blocks to render when expanded */
  children: React.ReactNode;
  className?: string;
  /** Initial open state. True when any child is actively streaming. Defaults to false. */
  defaultOpen?: boolean;
}

/** Format ms to compact string */
function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  return `${minutes}m ${remainingSeconds}s`;
}

export const ReasoningGroup = memo<ReasoningGroupProps>(
  ({ stepCount, totalDurationMs, children, className, defaultOpen }) => {
    const [isOpen, setIsOpen] = useState(() => defaultOpen ?? false);

    const summary = useMemo(() => {
      const steps = stepCount === 1 ? '1 step' : `${stepCount} steps`;
      const duration = totalDurationMs > 0 ? `, ${formatDuration(totalDurationMs)}` : '';
      return `${steps}${duration}`;
    }, [stepCount, totalDurationMs]);

    return (
      <div className={cn('text-sm', className)}>
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className={cn(
            'flex w-full items-center gap-2 py-1 px-0.5 -mx-0.5',
            'text-left text-muted-foreground hover:text-foreground',
            'rounded transition-colors'
          )}
          aria-expanded={isOpen}
          aria-label={`Reasoning: ${summary}`}
        >
          <Layers className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <span>
            Reasoning <span className="text-xs text-muted-foreground/60">({summary})</span>
          </span>
          <ChevronDown
            className={cn('ml-auto h-3 w-3 transition-transform', isOpen && 'rotate-180')}
          />
        </button>

        {isOpen && <div className="pl-2 pt-1 space-y-1">{children}</div>}
      </div>
    );
  }
);

ReasoningGroup.displayName = 'ReasoningGroup';

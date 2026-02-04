/**
 * ThinkingBlock - Collapsible "Agent Reasoning" block for extended thinking.
 *
 * Renders Claude's extended thinking content in a collapsible section
 * within assistant messages. Collapsed by default, shows summary line.
 *
 * Design: Warm, capable aesthetic per ui-design-spec.md v4.0
 * - Background: var(--ai-muted) with left border accent
 * - Monospace font for thinking content
 * - Duration + token estimate in footer
 */

'use client';

import { memo, useState, useCallback } from 'react';
import { Brain, ChevronDown, ChevronRight, ShieldAlert } from 'lucide-react';
import { cn } from '@/lib/utils';

/** Sentinel value emitted by backend for redacted thinking blocks (G-04) */
const REDACTED_SENTINEL = '[Thinking redacted by safety system]';

interface ThinkingBlockProps {
  /** Thinking content text */
  content: string;
  /** Duration of thinking phase in milliseconds */
  durationMs?: number;
  /** Whether thinking is actively streaming */
  isStreaming: boolean;
  /** Additional CSS classes */
  className?: string;
}

/** Format milliseconds to human-readable duration (e.g., "4.2s", "1m 12s") */
function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  return `${minutes}m ${remainingSeconds}s`;
}

/** Rough token estimate: ~4 chars per token */
function estimateTokens(text: string): number {
  return Math.round(text.length / 4);
}

export const ThinkingBlock = memo<ThinkingBlockProps>(
  ({ content, durationMs, isStreaming, className }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    const toggleExpanded = useCallback(() => {
      setIsExpanded((prev) => !prev);
    }, []);

    if (!content) return null;

    const isRedacted = content.includes(REDACTED_SENTINEL);
    const tokenEstimate = estimateTokens(content);
    const ChevronIcon = isExpanded ? ChevronDown : ChevronRight;

    return (
      <div
        className={cn(
          'rounded-[10px] border-l-[3px] border-l-ai/30 bg-ai-muted',
          'overflow-hidden transition-all duration-200 ease-out',
          className
        )}
        role="region"
        aria-label="Agent reasoning"
      >
        {/* Header — always visible */}
        <button
          type="button"
          onClick={toggleExpanded}
          className={cn(
            'flex w-full items-center gap-2 px-3 py-2',
            'text-left text-sm text-ai hover:bg-ai-muted/80',
            'transition-colors duration-150'
          )}
          aria-expanded={isExpanded}
          aria-controls="thinking-content"
        >
          {isRedacted ? (
            <ShieldAlert className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          ) : (
            <Brain className="h-3.5 w-3.5 shrink-0" />
          )}
          <span className="font-medium">
            {isRedacted ? 'Reasoning Redacted' : 'Agent Reasoning'}
          </span>

          {/* Summary info */}
          <span className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
            {isStreaming && (
              <span className="inline-flex items-center gap-1">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-ai" />
                Thinking
              </span>
            )}
            {!isStreaming && durationMs != null && <span>{formatDuration(durationMs)}</span>}
            {!isStreaming && tokenEstimate > 0 && (
              <span>{tokenEstimate.toLocaleString()} tokens</span>
            )}
            <ChevronIcon className="h-3.5 w-3.5" />
          </span>
        </button>

        {/* Content — expandable */}
        {isExpanded && (
          <div
            id="thinking-content"
            className={cn('border-t border-ai/10 px-3 py-2', 'max-h-[400px] overflow-y-auto')}
          >
            <pre
              className={cn(
                'whitespace-pre-wrap break-words font-mono text-[13px] leading-relaxed text-foreground/80',
                isStreaming && 'opacity-60'
              )}
            >
              {content}
              {isStreaming && (
                <span className="ml-0.5 inline-block h-4 w-[2px] animate-pulse bg-ai" />
              )}
            </pre>
          </div>
        )}
      </div>
    );
  }
);

ThinkingBlock.displayName = 'ThinkingBlock';

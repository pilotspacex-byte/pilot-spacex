/**
 * ThinkingBlock - Frosted glass collapsible for extended thinking.
 *
 * Renders Claude's extended thinking content with real-time elapsed
 * timer during streaming, auto-collapse on completion, and interrupted state.
 *
 * Design: Warm, capable aesthetic per ui-design-spec.md v4.0
 * - Frosted glass: glass-subtle + bg-ai-muted
 * - Left border accent with ai-pulse during streaming
 * - shadcn Collapsible for expand/collapse
 * - Monospace font for thinking content
 *
 * @module features/ai/ChatView/MessageList/ThinkingBlock
 */

'use client';

import { memo, useState, useCallback, useEffect, useRef } from 'react';
import { Brain, ChevronDown, ChevronRight, ShieldAlert } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useElapsedTime } from '@/hooks/useElapsedTime';
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '@/components/ui/collapsible';
import { Badge } from '@/components/ui/badge';

/** Sentinel value emitted by backend for redacted thinking blocks (G-04) */
const REDACTED_SENTINEL = '[Thinking redacted by safety system]';

/** Auto-collapse delay after streaming ends (ms) */
const AUTO_COLLAPSE_DELAY_MS = 300;

interface ThinkingBlockProps {
  /** Thinking content text */
  content: string;
  /** Duration of thinking phase in milliseconds (completed blocks) */
  durationMs?: number;
  /** Whether thinking is actively streaming */
  isStreaming: boolean;
  /** Timestamp (ms) when thinking started, for live timer */
  thinkingStartedAt?: number | null;
  /** Whether the stream was interrupted by user */
  interrupted?: boolean;
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
  return Math.ceil(text.length / 4);
}

/**
 * Hook to manage auto-collapse of a panel after streaming ends.
 * Open while streaming, auto-collapse ONCE after delay when streaming stops.
 * User can manually toggle at any time without re-triggering auto-collapse.
 */
function useStreamingCollapse(isStreaming: boolean) {
  const [prevStreaming, setPrevStreaming] = useState(isStreaming);
  const [isOpen, setIsOpen] = useState(isStreaming);
  // Track whether auto-collapse already fired for this streaming cycle.
  // Starts true when not streaming (no cycle to collapse from).
  const didAutoCollapse = useRef(!isStreaming);

  // Detect streaming transitions via derived state pattern
  if (isStreaming !== prevStreaming) {
    setPrevStreaming(isStreaming);
    if (isStreaming) {
      setIsOpen(true);
      didAutoCollapse.current = false; // Reset for new streaming cycle
    }
  }

  // Auto-collapse ONCE after streaming ends with delay
  useEffect(() => {
    if (isStreaming || !isOpen || didAutoCollapse.current) return;

    const timer = setTimeout(() => {
      setIsOpen(false);
      didAutoCollapse.current = true;
    }, AUTO_COLLAPSE_DELAY_MS);

    return () => clearTimeout(timer);
  }, [isStreaming, isOpen]);

  const toggle = useCallback(() => {
    setIsOpen((prev) => !prev);
  }, []);

  return { isOpen, setIsOpen, toggle } as const;
}

export const ThinkingBlock = memo<ThinkingBlockProps>(
  ({ content, durationMs, isStreaming, thinkingStartedAt, interrupted = false, className }) => {
    const { isOpen, setIsOpen, toggle: handleToggle } = useStreamingCollapse(isStreaming);
    const elapsed = useElapsedTime(thinkingStartedAt ?? null, isStreaming);

    if (!content) return null;

    const isRedacted = content.includes(REDACTED_SENTINEL);
    const tokenEstimate = estimateTokens(content);
    const ChevronIcon = isOpen ? ChevronDown : ChevronRight;

    return (
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <div
          className={cn(
            'glass-subtle rounded-[var(--radius-md)] bg-ai-muted',
            'border-l-[4px] border-l-ai',
            'overflow-hidden transition-shadow duration-150',
            'hover:shadow-warm-sm',
            isStreaming && 'motion-safe:animate-ai-pulse',
            className
          )}
          role="region"
          aria-label="Agent reasoning"
        >
          {/* Header - always visible */}
          <CollapsibleTrigger asChild>
            <button
              type="button"
              onClick={handleToggle}
              className={cn(
                'flex w-full items-center gap-2 px-3 py-2',
                'text-left text-sm text-ai hover:bg-ai-muted/80',
                'transition-colors duration-150'
              )}
              aria-expanded={isOpen}
            >
              {isRedacted ? (
                <ShieldAlert className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              ) : (
                <Brain className="h-3.5 w-3.5 shrink-0" />
              )}

              {/* Label: streaming / completed / interrupted */}
              <span className="font-medium">
                {isRedacted
                  ? 'Reasoning Redacted'
                  : interrupted
                    ? 'Interrupted'
                    : isStreaming
                      ? 'Thinking...'
                      : durationMs != null
                        ? `Thought for ${formatDuration(durationMs)}`
                        : 'Agent Reasoning'}
              </span>

              {/* Right-aligned meta */}
              <span className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
                {isStreaming && (
                  <>
                    <span className="h-1.5 w-1.5 motion-safe:animate-pulse rounded-full bg-ai" />
                    <span className="font-mono text-xs tabular-nums text-ai">{elapsed}</span>
                  </>
                )}
                {!isStreaming && !interrupted && tokenEstimate > 0 && (
                  <Badge variant="secondary" className="text-xs">
                    ~{tokenEstimate.toLocaleString()} tokens
                  </Badge>
                )}
                <ChevronIcon className="h-3.5 w-3.5" />
              </span>
            </button>
          </CollapsibleTrigger>

          {/* Content - collapsible */}
          <CollapsibleContent>
            <div
              className={cn(
                'border-t border-ai/10 px-3 py-2',
                'max-h-[400px] overflow-y-auto scrollbar-thin'
              )}
            >
              <pre
                className={cn(
                  'whitespace-pre-wrap break-words font-mono text-[13px]',
                  'leading-relaxed text-foreground/80',
                  isStreaming && 'opacity-60'
                )}
              >
                {content}
                {isStreaming && (
                  <span className="ml-0.5 inline-block h-4 w-[2px] motion-safe:animate-pulse bg-ai" />
                )}
              </pre>
            </div>
          </CollapsibleContent>
        </div>
      </Collapsible>
    );
  }
);

ThinkingBlock.displayName = 'ThinkingBlock';

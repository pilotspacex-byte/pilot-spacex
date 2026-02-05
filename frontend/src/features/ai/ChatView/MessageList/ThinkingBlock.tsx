/**
 * ThinkingBlock - Minimal inline toggle for extended thinking.
 *
 * Renders Claude's extended thinking content with real-time elapsed
 * timer during streaming, auto-collapse on completion, and interrupted state.
 *
 * Design: Claude.ai style - minimal, non-intrusive
 * - Single-line toggle row with status icon + chevron
 * - No frosted glass / borders / card styling
 * - Indented muted text for content
 *
 * @module features/ai/ChatView/MessageList/ThinkingBlock
 */

'use client';

import { memo, useCallback, useEffect, useReducer } from 'react';
import { Check, ChevronDown, ChevronUp, Loader2, ShieldAlert } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useElapsedTime } from '@/hooks/useElapsedTime';

/** Sentinel value emitted by backend for redacted thinking blocks (G-04) */
const REDACTED_SENTINEL = '[Thinking redacted by safety system]';

/** Auto-collapse delay after streaming ends (ms) */
const AUTO_COLLAPSE_DELAY_MS = 300;

/** Collapse state for streaming panels */
type CollapseState = {
  isOpen: boolean;
  didAutoCollapse: boolean;
  prevStreaming: boolean;
};

type CollapseAction =
  | { type: 'STREAMING_STARTED' }
  | { type: 'STREAMING_STOPPED' }
  | { type: 'TOGGLE' }
  | { type: 'AUTO_COLLAPSE' };

function collapseReducer(state: CollapseState, action: CollapseAction): CollapseState {
  switch (action.type) {
    case 'STREAMING_STARTED':
      return { isOpen: true, didAutoCollapse: false, prevStreaming: true };
    case 'STREAMING_STOPPED':
      return { ...state, prevStreaming: false };
    case 'TOGGLE':
      return { ...state, isOpen: !state.isOpen };
    case 'AUTO_COLLAPSE':
      return { ...state, isOpen: false, didAutoCollapse: true };
    default:
      return state;
  }
}

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

/**
 * Hook to manage auto-collapse of a panel after streaming ends.
 * Open while streaming, auto-collapse ONCE after delay when streaming stops.
 * User can manually toggle at any time without re-triggering auto-collapse.
 *
 * Uses useReducer to avoid lint issues with setState in effects.
 */
function useStreamingCollapse(isStreaming: boolean) {
  const [state, dispatch] = useReducer(collapseReducer, isStreaming, (streaming) => ({
    isOpen: streaming,
    didAutoCollapse: !streaming,
    prevStreaming: streaming,
  }));

  // Detect streaming start/stop transitions
  useEffect(() => {
    if (isStreaming && !state.prevStreaming) {
      dispatch({ type: 'STREAMING_STARTED' });
    } else if (!isStreaming && state.prevStreaming) {
      dispatch({ type: 'STREAMING_STOPPED' });
    }
  }, [isStreaming, state.prevStreaming]);

  // Auto-collapse ONCE after streaming ends with delay
  useEffect(() => {
    if (isStreaming || !state.isOpen || state.didAutoCollapse) return;

    const timer = setTimeout(() => {
      dispatch({ type: 'AUTO_COLLAPSE' });
    }, AUTO_COLLAPSE_DELAY_MS);

    return () => clearTimeout(timer);
  }, [isStreaming, state.isOpen, state.didAutoCollapse]);

  const toggle = useCallback(() => {
    dispatch({ type: 'TOGGLE' });
  }, []);

  return { isOpen: state.isOpen, toggle } as const;
}

export const ThinkingBlock = memo<ThinkingBlockProps>(
  ({ content, durationMs, isStreaming, thinkingStartedAt, interrupted = false, className }) => {
    const { isOpen, toggle: handleToggle } = useStreamingCollapse(isStreaming);
    const elapsed = useElapsedTime(thinkingStartedAt ?? null, isStreaming);

    if (!content) return null;

    const isRedacted = content.includes(REDACTED_SENTINEL);
    const ChevronIcon = isOpen ? ChevronUp : ChevronDown;

    return (
      <div className={cn('text-sm', className)}>
        {/* Toggle row - minimal inline style */}
        <button
          type="button"
          onClick={handleToggle}
          className={cn(
            'flex w-full items-center gap-2 py-1 px-0.5 -mx-0.5',
            'text-left text-muted-foreground hover:text-foreground',
            'rounded transition-colors'
          )}
          aria-expanded={isOpen}
          aria-label="Agent reasoning"
        >
          {/* Status indicator */}
          {isRedacted ? (
            <ShieldAlert className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          ) : isStreaming ? (
            <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-ai motion-reduce:animate-none" />
          ) : (
            <Check className="h-3.5 w-3.5 shrink-0 text-primary" />
          )}

          {/* Label */}
          <span>
            {isRedacted
              ? 'Reasoning redacted'
              : interrupted
                ? 'Thinking interrupted'
                : isStreaming
                  ? 'Thinking...'
                  : durationMs != null
                    ? `Thought for ${formatDuration(durationMs)}`
                    : 'Thought'}
          </span>

          <span className="ml-auto flex items-center gap-1.5">
            {isStreaming && (
              <span className="font-mono text-xs tabular-nums text-ai">{elapsed}</span>
            )}
            <ChevronIcon className="h-3 w-3" />
          </span>
        </button>

        {/* Collapsible content - indented text, no border */}
        {isOpen && (
          <div className="pl-2 pt-1 pb-2">
            <pre
              className={cn(
                'whitespace-pre-wrap break-words font-mono text-xs',
                'leading-relaxed text-muted-foreground',
                isStreaming && 'opacity-70'
              )}
            >
              {content}
              {isStreaming && (
                <span className="ml-0.5 inline-block h-3 w-[2px] animate-pulse bg-ai motion-reduce:animate-none" />
              )}
            </pre>
          </div>
        )}
      </div>
    );
  }
);

ThinkingBlock.displayName = 'ThinkingBlock';

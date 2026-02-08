/**
 * ToolCallCard - Minimal inline toggle for individual tool call execution.
 *
 * Displays human-readable tool name, status icon with color coding,
 * elapsed/completed duration, collapsible input/output detail,
 * partial input streaming indicator (G-09), and error messages.
 *
 * Design: Claude.ai style - minimal, non-intrusive
 * - Single-line toggle: "Calling X..." or "Used X"
 * - No bordered card styling
 * - Indented detail sections
 *
 * @module features/ai/ChatView/MessageList/ToolCallCard
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import { observer } from 'mobx-react-lite';
import { Loader2, Settings, XCircle, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useElapsedTime } from '@/hooks/useElapsedTime';
import { getToolDisplayName } from '../constants';
import type { ToolCall } from '@/stores/ai/types/conversation';

interface ToolCallCardProps {
  toolCall: ToolCall;
  className?: string;
}

/** Format duration in milliseconds to a compact string (e.g., "0.8s", "2.1s") */
function formatDuration(ms: number): string {
  const seconds = ms / 1000;
  if (seconds < 10) {
    return `${seconds.toFixed(1)}s`;
  }
  return `${Math.floor(seconds)}s`;
}

/** Max characters for input preview in the toggle row */
const INPUT_PREVIEW_MAX = 60;

/** Try to pretty-format partial JSON input. Falls back to raw string. */
function formatPartialInput(partial: string): string {
  try {
    const parsed = JSON.parse(partial);
    return JSON.stringify(parsed, null, 2);
  } catch {
    // Incomplete JSON — show raw
    return partial;
  }
}

/** Generate a short one-line preview from tool input or partial input. */
function getInputPreview(input: Record<string, unknown>, partialInput?: string): string | null {
  // Prefer structured input (completed tools)
  const keys = Object.keys(input);
  if (keys.length > 0) {
    // Show first key-value pair as preview
    const firstKey = keys[0]!;
    const value = input[firstKey];
    const valueStr = typeof value === 'string' ? value : JSON.stringify(value);
    const preview = `${firstKey}: ${valueStr}`;
    if (preview.length > INPUT_PREVIEW_MAX) {
      return preview.slice(0, INPUT_PREVIEW_MAX - 1) + '\u2026';
    }
    return preview;
  }

  // Fall back to partial input (streaming)
  if (partialInput) {
    // Try to parse partial JSON for first key-value
    const match = partialInput.match(/"(\w+)":\s*"?([^",}]+)/);
    if (match) {
      const preview = `${match[1]}: ${match[2]}`;
      if (preview.length > INPUT_PREVIEW_MAX) {
        return preview.slice(0, INPUT_PREVIEW_MAX - 1) + '\u2026';
      }
      return preview;
    }
  }

  return null;
}

export const ToolCallCard = observer<ToolCallCardProps>(({ toolCall, className }) => {
  const status = toolCall.status || 'pending';
  const displayName = getToolDisplayName(toolCall.name);
  const inputPreview = getInputPreview(toolCall.input, toolCall.partialInput);

  // Elapsed time: capture start time on mount via lazy state initializer (pure)
  const [startTime] = useState(() => Date.now());
  const isRunning = status === 'pending';
  const elapsed = useElapsedTime(startTime, isRunning);

  const [isOpen, setIsOpen] = useState(false);
  const autoExpandedRef = useRef(false);

  // Auto-expand when partialInput starts streaming (so user sees tool input in real-time)
  useEffect(() => {
    if (toolCall.partialInput && !autoExpandedRef.current && isRunning) {
      setIsOpen(true);
      autoExpandedRef.current = true;
    }
  }, [toolCall.partialInput, isRunning]);

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
    <div className={cn('text-sm', className)}>
      {/* Toggle row - inline style like Claude.ai */}
      <button
        type="button"
        onClick={() => hasDetail && setIsOpen(!isOpen)}
        className={cn(
          'flex w-full items-center gap-2 py-1 px-0.5 -mx-0.5',
          'text-left text-muted-foreground hover:text-foreground',
          'rounded transition-colors',
          !hasDetail && 'cursor-default'
        )}
        disabled={!hasDetail}
        aria-expanded={hasDetail ? isOpen : undefined}
        aria-label={`${displayName} tool call`}
      >
        {/* Status icon - compact */}
        {status === 'pending' && (
          <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-ai motion-reduce:animate-none" />
        )}
        {status === 'completed' && (
          <Settings className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        )}
        {status === 'failed' && <XCircle className="h-3.5 w-3.5 shrink-0 text-destructive" />}

        {/* Label: "Calling X..." or "Used X" with input preview */}
        <span className="min-w-0 flex items-baseline gap-1.5 truncate">
          <span>{status === 'pending' ? `${displayName}...` : `${displayName}`}</span>
          {inputPreview && (
            <span className="font-mono text-xs text-muted-foreground/60 truncate">
              {inputPreview}
            </span>
          )}
        </span>

        {/* Duration + chevron */}
        <span className="ml-auto flex shrink-0 items-center gap-1.5">
          {durationText && <span className="font-mono text-xs tabular-nums">{durationText}</span>}
          {hasDetail && (
            <ChevronDown className={cn('h-3 w-3 transition-transform', isOpen && 'rotate-180')} />
          )}
        </span>
      </button>

      {/* Error inline */}
      {toolCall.errorMessage && (
        <p className="pl-5 text-xs text-destructive">{toolCall.errorMessage}</p>
      )}

      {/* Collapsible detail - indented, no border */}
      {isOpen && hasDetail && (
        <div className="pl-5 pt-1 space-y-1.5">
          {/* Partial input while streaming (G-09) — auto-expanded */}
          {hasInput && toolCall.partialInput ? (
            <div>
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                Input
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-ai motion-reduce:animate-none" />
              </span>
              <pre className="text-xs bg-muted/30 p-1.5 rounded mt-0.5 overflow-x-auto max-h-[200px] overflow-y-auto opacity-60 font-mono whitespace-pre-wrap break-words">
                {formatPartialInput(toolCall.partialInput)}
              </pre>
            </div>
          ) : Object.keys(toolCall.input).length > 0 ? (
            <div>
              <span className="text-xs text-muted-foreground">Input:</span>
              <pre className="text-xs bg-muted/30 p-1.5 rounded mt-0.5 overflow-x-auto font-mono">
                {JSON.stringify(toolCall.input, null, 2)}
              </pre>
            </div>
          ) : null}

          {/* Output */}
          {hasOutput && (
            <div>
              <span className="text-xs text-muted-foreground">Output:</span>
              <pre className="text-xs bg-muted/30 p-1.5 rounded mt-0.5 overflow-x-auto font-mono">
                {typeof toolCall.output === 'string'
                  ? toolCall.output
                  : JSON.stringify(toolCall.output, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
});

ToolCallCard.displayName = 'ToolCallCard';

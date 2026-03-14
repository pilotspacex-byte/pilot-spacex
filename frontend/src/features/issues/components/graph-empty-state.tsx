'use client';

/**
 * GraphEmptyState — loading, empty, and error placeholder for knowledge graph.
 *
 * Three variants:
 *  - loading: pulsing skeleton circles with SVG connector lines
 *  - empty:   SVG placeholder + "No knowledge graph yet" + optional chat CTA
 *  - error:   error message + optional retry button
 */

import { Skeleton } from '@/components/ui/skeleton';

export interface GraphEmptyStateProps {
  variant: 'loading' | 'empty' | 'error';
  onRetry?: () => void;
  onOpenChat?: () => void;
  /** Container height in px. Defaults to 200. */
  height?: number;
}

export function GraphEmptyState({
  variant,
  onRetry,
  onOpenChat,
  height = 200,
}: GraphEmptyStateProps) {
  if (variant === 'loading') {
    return (
      <div
        role="status"
        aria-label="Loading knowledge graph"
        className="flex items-center justify-center gap-6"
        style={{ height }}
      >
        {/* SVG connector lines behind the circles */}
        <svg
          aria-hidden="true"
          className="absolute pointer-events-none opacity-30"
          width="160"
          height="40"
          viewBox="0 0 160 40"
        >
          <line x1="30" y1="20" x2="65" y2="20" stroke="currentColor" strokeWidth="1.5" />
          <line x1="95" y1="20" x2="130" y2="20" stroke="currentColor" strokeWidth="1.5" />
        </svg>

        <Skeleton className="size-10 rounded-full shrink-0" />
        <Skeleton className="size-8 rounded-full shrink-0" />
        <Skeleton className="size-10 rounded-full shrink-0" />
      </div>
    );
  }

  if (variant === 'error') {
    return (
      <div
        role="alert"
        className="flex flex-col items-center justify-center gap-3 text-center"
        style={{ height }}
      >
        <p className="text-sm text-muted-foreground">Failed to load knowledge graph</p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="text-xs text-primary underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
          >
            Retry
          </button>
        )}
      </div>
    );
  }

  // empty
  return (
    <div className="flex flex-col items-center justify-center gap-3 text-center" style={{ height }}>
      {/* Abstract graph placeholder: diamond — circle — square */}
      <svg
        aria-hidden="true"
        width="96"
        height="28"
        viewBox="0 0 96 28"
        className="text-muted-foreground opacity-40"
      >
        {/* Connectors */}
        <line x1="18" y1="14" x2="34" y2="14" stroke="currentColor" strokeWidth="1.5" />
        <line x1="62" y1="14" x2="78" y2="14" stroke="currentColor" strokeWidth="1.5" />
        {/* Diamond (decision) */}
        <polygon
          points="8,14 14,8 20,14 14,20"
          stroke="currentColor"
          strokeWidth="1.5"
          fill="none"
        />
        {/* Circle (user/node) */}
        <circle cx="48" cy="14" r="8" stroke="currentColor" strokeWidth="1.5" fill="none" />
        {/* Square (issue) */}
        <rect
          x="78"
          y="6"
          width="16"
          height="16"
          stroke="currentColor"
          strokeWidth="1.5"
          fill="none"
          rx="2"
        />
      </svg>

      <p className="text-sm text-muted-foreground">No knowledge graph yet</p>
      <p className="mt-1 text-xs text-muted-foreground max-w-xs text-center">
        The knowledge graph visualizes relationships between your notes, issues, and code.
      </p>

      {onOpenChat && (
        <button
          type="button"
          onClick={onOpenChat}
          className="text-xs text-primary underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
        >
          Open AI Chat →
        </button>
      )}
    </div>
  );
}
